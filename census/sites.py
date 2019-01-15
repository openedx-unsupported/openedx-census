import collections
import csv

import attr
import opaque_keys
import opaque_keys.edx.keys

from census.helpers import (
    domain_from_url, is_chaff_domain, is_known, fingerprint, sniff_version
)

@attr.s(cmp=False, frozen=False)
class Site:
    # Stuff from the csv:
    url = attr.ib()
    latest_courses = attr.ib()
    is_gone = attr.ib()

    # Stuff that we scrape:
    current_courses = attr.ib(default=None)
    is_gone_now = attr.ib(default=False)
    course_ids = attr.ib(default=attr.Factory(collections.Counter))
    tried = attr.ib(default=attr.Factory(list))
    ssl_err = False
    custom_parser_err = False
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

    IGNORE_LINE_FRAGMENTS = [
        b"window.NREUM||(NREUM={})",
        b"<input type='hidden' name='csrfmiddlewaretoken'",
    ]

    def add_to_fingerprint(self, text):
        # Remove noise from the fingerprint.
        lines = text.splitlines(keepends=True)
        lines = [l for l in lines if not any(frag in l for frag in self.IGNORE_LINE_FRAGMENTS)]
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
