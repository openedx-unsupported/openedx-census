import collections
import csv
import re

import attr
import opaque_keys
import opaque_keys.edx.keys

from census.helpers import (
    domain_from_url, is_chaff_domain, is_known, fingerprint, sniff_version
)

@attr.s(cmp=False, frozen=False)
class Site:
    ## Stuff from the known sites csv:
    url = attr.ib(type=str)
    latest_courses = attr.ib(type=int)
    is_gone = attr.ib(type=bool)

    ## Stuff that we scrape:
    current_courses = attr.ib(default=None)
    is_gone_now = attr.ib(default=False)

    # Maps course-ids to number of instances of the course
    course_ids = attr.ib(factory=collections.Counter)

    # List of (strategy, traceback-string-or-none)
    tried = attr.ib(factory=list)
    ssl_err = attr.ib(default=False)
    custom_parser_err = attr.ib(default=False)
    time = attr.ib(default=None)
    fingerprint = attr.ib(default="")
    version = attr.ib(default=None)

    def __eq__(self, other):
        return self.url == other.url

    def __hash__(self):
        return hash(self.url)

    @classmethod
    def from_csv_row(cls, url, course_count, is_gone, **ignored):
        return cls(url, course_count, is_gone=='True')

    @classmethod
    def from_url(cls, url):
        return cls(clean_url(url), latest_courses=0, is_gone=False)

    # Ignore any line containing these strings.
    IGNORE_LINE_FRAGMENTS = [
        b"window.NREUM||(NREUM={})",
        b"<input type='hidden' name='csrfmiddlewaretoken'",
    ]

    # Regex replacements to remove noise from fingerprints.
    REMOVABLE_NOISE = [
        (r'<script type="[0-9a-fA-F]+-text/javascript"', r'<script type="XXX-text/javascript"'),
    ]

    def add_to_fingerprint(self, text):
        # Remove noise from the fingerprint.
        lines = text.splitlines(keepends=True)
        lines = [l for l in lines if not any(frag in l for frag in self.IGNORE_LINE_FRAGMENTS)]
        for pat, repl in self.REMOVABLE_NOISE:
            lines = [re.sub(pat, repl, l) for l in lines]
        lines.append(self.fingerprint.encode('ascii'))
        text = b''.join(lines)
        self.fingerprint = fingerprint(text)
        self.version = sniff_version(text)

    def should_update(self):
        """Should we update this site in the database?"""
        if self.is_gone:
            if not self.is_gone_now and self.current_courses:
                # Was gone, now not.
                return True
        else:
            if self.is_gone_now:
                # Used to be here, but now not.
                return True
        if not self.current_courses:
            return False
        if self.current_courses != self.latest_courses:
            return True
        return False


@attr.s()
class HashedSite:
    fingerprint = attr.ib(default=None)
    sites = attr.ib(default=attr.Factory(list))

    def current_courses(self):
        return self.sites[0].current_courses

    def all_chaff(self):
        return all(is_chaff_domain(domain_from_url(site.url)) for site in self.sites)

    def any_known(self, known_domains):
        return any(is_known(site, known_domains) for site in self.sites)

    def best_url(self):
        non_chaff = [site for site in self.sites if not is_chaff_domain(site.url)]
        if non_chaff:
            url = non_chaff[0].url
        else:
            url = self.sites[0].url
        return url


def clean_url(url):
    url = url.strip().strip("/")
    if not url.startswith("http"):
        url = "http://" + url
    return url

def read_sites_csv(csv_file):
    with open(csv_file) as f:
        for row in csv.DictReader(f):
            row['url'] = clean_url(row['url'])
            row['course_count'] = int(row['course_count'] or 0)
            yield Site.from_csv_row(**row)

def read_sites_flat(flat_file):
    with open(flat_file) as f:
        sites = [Site.from_url(url) for url in f]
    return sites

def totals(sites):
    old = new = 0
    for site in sites:
        old += site.latest_courses
        new += site.current_courses or site.latest_courses
    return old, new

def courses_and_orgs(sites):
    """Collate courses, orgs, and course ids from scraped sites.

    Returns three values:

        - all_courses is a dict mapping course_ids to a set of sites running that
          course.

        - all_orgs is a dict mapping organization ids to a set of sites running
          courses in that organization.

        - all_course_ids is a set of all course ids.

    """
    all_courses = collections.defaultdict(set)
    all_orgs = collections.defaultdict(set)
    all_course_ids = set()
    for site in sites:
        for course_id, num in site.course_ids.items():
            all_course_ids.add(course_id)
            try:
                key = opaque_keys.edx.keys.CourseKey.from_string(course_id)
                all_orgs[key.org].add(site)
            except opaque_keys.InvalidKeyError:
                course = course_id
            else:
                course = f"{key.org}+{key.course}"
            all_courses[course].add(site)
    return all_courses, all_orgs, all_course_ids


SYNDICATORS = ['Microsoft', 'BigDataUniversity']

def overcount(all_courses):
    """Compute the number of duplicate courses.

    This is recorded as the "overcount": how much to subtract from the sum of
    the number of courses for each site, to get the total number of courses.

    `all_courses` is a dict mapping course_ids to a set of sites running that
    course.

    Returns: an integer, the overcount.
    """
    # If a course is run by 5 sites, then 4 go into the overcount.
    true_dups = sum(len(s) - 1 for s in all_courses.values())

    # A trickier case: some sites re-label courses with a new organization.
    # This happens with Microsoft courses a lot.
    reorged = 0
    org_courses = [tuple(id.split("+")) for id in all_courses.keys()]
    org_courses = [t for t in org_courses if len(t) == 2]
    for syn_org in SYNDICATORS:
        syn_courses = {
            course for org, course in org_courses
            if org == syn_org and len(course) > 3 and course[0].isalpha()
            }
        other_orgs = collections.defaultdict(set)
        for org, course in org_courses:
            if org == syn_org:
                continue
            if course in syn_courses:
                other_orgs[org].add(course)

        # orgs maps organizations onto a set of the syndicator's course ids
        # they run.  Just a course id isn't unique enough ("CS100"), so we
        # look for orgs with 3 or more of those course ids.
        for org, courses in other_orgs.items():
            if len(courses) < 3:
                continue
            #print(f"Org {org} has {len(courses)} in common with {syn_org}")
            reorged += len(courses)

    return true_dups + reorged
