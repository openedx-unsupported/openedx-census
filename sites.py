import collections
import csv

import attr
import opaque_keys
import opaque_keys.edx.keys


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
    time = attr.ib(default=None)
    fingerprint = attr.ib(default=None)

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
            except opaque_keys.InvalidKeyError:
                course = course_id
            else:
                course = f"{key.org}+{key.course}"
            all_courses[course].add(site)
            all_orgs[key.org].add(site)
    return all_courses, all_orgs, all_course_ids
