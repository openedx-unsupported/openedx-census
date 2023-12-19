import collections
import csv
import re

import attr
import opaque_keys
import opaque_keys.edx.keys

from census.helpers import (
    domain_from_url, is_chaff_domain, is_known, calc_fingerprint, sniff_version,
    sniff_tags, emails_in_text, hostname
)

@attr.s
class Attempt:
    """A use of a strategy on a site."""
    strategy = attr.ib(default="")
    courses = attr.ib(default=None)
    error = attr.ib(default=None)



@attr.s(cmp=False, frozen=False)
class Site:
    ## Stuff from the known sites csv:
    url = attr.ib(type=str)
    latest_courses = attr.ib(type=int)
    is_gone = attr.ib(type=bool)

    ## Stuff that we scrape:
    current_courses = attr.ib(default=None)
    is_gone_now = attr.ib(default=False)
    # Is there any indication at all that this is an open edx site? For use
    # when there are no courses.
    is_openedx = attr.ib(default=False)

    # Maps course-ids to number of instances of the course
    course_ids = attr.ib(factory=collections.Counter)

    # List of Attempt's
    tried = attr.ib(factory=list)

    ssl_err = attr.ib(default=False)
    custom_parser_err = attr.ib(default=False)
    time = attr.ib(default=None)
    fingerprint = attr.ib(default="")
    version = attr.ib(default=None)
    tags = attr.ib(factory=set)

    # Other random things from the site
    emails = attr.ib(factory=list)
    other_info = attr.ib(factory=list)

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
        (rb'<script type="[0-9a-fA-F]+-text/javascript"', rb'<script type="XXX-text/javascript"'),
        # <script src="https://ajax.cloudflare.com/cdn-cgi/scripts/cb7744ae/cloudflare-static/rocket-loader.min.js" data-cf-settings="4d25b03f3332116d5fb64ead-|49" defer="">
        (rb' data-cf-settings="[0-9a-fA-F]+-\|', rb' data-cf-settings="XXX-\|'),
    ]

    def process_text(self, text, fingerprint=True, type="html", emails=True):
        """
        Text retrieved from the site, processed for a few things.
        """
        if fingerprint:
            # Remove noise from the fingerprint.
            lines = text.splitlines(keepends=True)
            lines = [l for l in lines if not any(frag in l for frag in self.IGNORE_LINE_FRAGMENTS)]
            for pat, repl in self.REMOVABLE_NOISE:
                lines = [re.sub(pat, repl, l) for l in lines]
            lines.append(self.fingerprint.encode('ascii'))
            text = b''.join(lines)
            self.fingerprint = calc_fingerprint(text)
        if type == "html":
            version = sniff_version(text)
            if version:
                self.version = version
            self.tags.update(sniff_tags(self.url, text))
        if emails:
            self.emails.extend(emails_in_text(text))

    def got_response(self, url, response):
        actual_host = hostname(str(response.url))
        if hostname(url) != actual_host:
            self.other_info.append(actual_host)

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

    def styled_tags(self):
        """Return a list of (tag_text, tag_style)"""
        tags = []
        def add_tag(text, style=None):
            tags.append((text, style))
        for t in self.tags:
            add_tag(t)
        if self.is_gone_now:
            add_tag("Gone")
        elif self.is_gone:
            add_tag("Back")
        if self.ssl_err:
            add_tag("SSL")
        if self.custom_parser_err:
            add_tag("Custom parser error", "bad")
        if self.version:
            add_tag(self.version, "version")
        return tags

    def attempt_course_count(self):
        """What's the course count for the attempts so far?"""
        return max((attempt.courses for attempt in self.tried if attempt.courses is not None), default=None)


@attr.s()
class HashedSite:
    fingerprint = attr.ib(default=None)
    sites = attr.ib(default=attr.Factory(list))
    version = attr.ib(default=None)
    is_new = attr.ib(default=False)

    def current_courses(self):
        return self.sites[0].current_courses

    def all_chaff(self):
        return all(is_chaff_domain(domain_from_url(site.url)) for site in self.sites)

    def any_known(self, known_domains):
        return any(is_known(site, known_domains) for site in self.sites)

    def all_ssl_err(self):
        return all(site.ssl_err for site in self.sites)

    def tags(self):
        return set(t for site in self.sites for t in site.tags)

    def other_info(self):
        return set(inf for site in self.sites for inf in site.other_info)

    def best_url(self):
        site_urls = [site.url for site in self.sites]
        non_chaff = [url for url in site_urls if not is_chaff_domain(domain_from_url(url))]
        urls = non_chaff or site_urls
        urls = non_sub_urls(urls)
        return urls[0]


def non_sub_urls(urls):
    """Return urls that are not subdomains of other urls."""
    domain_parts = [domain_from_url(u).split(".") for u in urls]
    def is_prefix(dp1, dp2):
        return dp1 != dp2 and dp2[len(dp2)-len(dp1):] == dp1
    non_sub_doms = [".".join(d) for d in domain_parts if not any(is_prefix(d2, d) for d2 in domain_parts)]
    non_subs = [u for u in urls if domain_from_url(u) in non_sub_doms]
    return non_subs


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
