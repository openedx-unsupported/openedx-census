#!/usr/bin/env python
"""Automate the process of counting courses on Open edX sites."""

import asyncio
import collections
import csv
import json
import logging
import pprint
import re
import time
import traceback
import urllib.parse
from xml.sax.saxutils import escape

import attr
import click
import opaque_keys
import opaque_keys.edx.keys
import requests

from helpers import ScrapeFail
from html_writer import HtmlOutlineWriter
from keys import username, password
from session import SmartSession
from site_patterns import find_site_functions

# We don't use anything from this module, it just registers all the parsers.
import sites


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
    time = attr.ib(default=None)

    def __eq__(self, other):
        return self.url == other.url

    def __hash__(self):
        return hash(self.url)

    @classmethod
    def from_csv_row(cls, url, course_count, is_gone, **ignored):
        return cls(url, course_count, is_gone=='True')

    @classmethod
    def from_url(cls, url):
        return cls(url, latest_courses=0, is_gone=False)

    def should_update(self):
        """Should we update this site in the database?"""
        if self.is_gone != self.is_gone_now:
            return True
        if not self.current_courses:
            return False
        if self.current_courses != self.latest_courses:
            return True
        return False


STATS_SITE = "http://openedxstats.herokuapp.com"
UPDATE_JSON = "update.json"
SITES_CSV = "sites.csv"


MAX_REQUESTS = 30
TIMEOUT = 20
USER_AGENT = "Open edX census-taker. Tell us about your site: oscm+census@edx.org"

GONE_MSGS = [
    "Cannot connect to host",
    "Bad Gateway",
]

async def parse_site(site, session):
    start = time.time()
    for parser, args, kwargs in find_site_functions(site.url):
        try:
            site.current_courses = await parser(site, session, *args, **kwargs)
        except ScrapeFail as err:
            site.tried.append((parser.__name__, f"{err.__class__.__name__}: {err}"))
        except Exception as exc:
            site.tried.append((parser.__name__, traceback.format_exc()))
            if any(msg in str(exc) for msg in GONE_MSGS):
                site.is_gone_now = True
                char = 'X'
                break
        else:
            site.tried.append((parser.__name__, None))
            char = '.'
            break
    else:
        char = 'E'

    print(char, end='', flush=True)
    site.time = time.time() - start


async def run(sites):
    tasks = []

    headers = {
        'User-Agent': USER_AGENT,
    }
    async with SmartSession(max_requests=MAX_REQUESTS, timeout=TIMEOUT, headers=headers) as session:
        for site in sites:
            task = asyncio.ensure_future(parse_site(site, session))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        print()

def scrape_sites(sites):
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(run(sites))
    # Some exceptions go to stderr and then to my except clause? Shut up.
    loop.set_exception_handler(lambda loop, context: None)
    loop.run_until_complete(future)

def read_sites_file(f):
    for row in csv.DictReader(f):
        url = row['url'].strip().strip("/")
        if not url.startswith("http"):
            url = "http://" + url
        row['url'] = url

        row['course_count'] = int(row['course_count'] or 0)

        yield row

def read_sites(csv_file):
    with open(csv_file) as f:
        for site in read_sites_file(f):
            yield Site.from_csv_row(**site)

@click.group(help=__doc__)
def cli():
    pass

@cli.command()
@click.option('--log', 'log_level', type=str, default='info')
@click.option('--min', type=int, default=1)
@click.option('--gone', is_flag=True)
@click.option('--site', is_flag=True)
@click.argument('site_patterns', nargs=-1)
def scrape(log_level, min, gone, site, site_patterns):
    """Visit sites and count their courses."""
    logging.basicConfig(level=log_level.upper())
    if site:
        # Exact sites provided on the command line
        sites = [Site.from_url(u) for u in site_patterns]
    else:
        # Make the list of sites we're going to scrape.
        sites = list(read_sites(SITES_CSV))
        sites = [s for s in sites if s.latest_courses >= min]
        if site_patterns:
            sites = [s for s in sites if any(re.search(p, s.url) for p in site_patterns)]
        if not gone:
            sites = [s for s in sites if not s.is_gone]

    if len(sites) == 1:
        print("1 site")
    else:
        print(f"{len(sites)} sites")

    # SCRAPE!
    scrape_sites(sites)

    # Prep data for reporting.
    sites_descending = sorted(sites, key=lambda s: s.latest_courses, reverse=True)
    old = new = 0
    for site in sites:
        old += site.latest_courses
        new += site.current_courses or site.latest_courses

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

    with open("course-ids.txt", "w") as f:
        f.write("".join(i + "\n" for i in sorted(all_course_ids)))

    text_report(sites_descending, old, new)
    html_report(sites_descending, old, new, all_courses, all_orgs)
    json_update(sites_descending, all_courses, include_overcount=(not site_patterns))


def text_report(sites, old, new):
    print(f"Found courses went from {old} to {new}")
    for site in sites:
        print(f"{site.url}: {site.latest_courses} --> {site.current_courses}")
        for strategy, tb in site.tried:
            if tb is not None:
                line = tb.splitlines()[-1]
            else:
                line = "Worked"
            print(f"    {strategy}: {line}")

def html_report(sites, old, new, all_courses, all_orgs):
    with open("sites.html", "w") as htmlout:
        CSS = """\
            html {
                font-family: sans-serif;
            }

            pre {
                font-family: Consolas, monospace;
            }

            .url {
                font-weight: bold;
            }
            .strategy {
                font-style: italic;
            }
            .tag {
                display: inline-block;
                font-size: 75%;
                margin: 0 .1em .1em;
                padding: 0 .3em;
                border-radius: 3px;
            }
            .tag.slow {
                background: #d5efa7;
            }
            .tag.none {
                background: #f09393;
            }
            .tag.drastic {
                background: #ebe377;
            }

        """

        writer = HtmlOutlineWriter(htmlout, css=CSS, title=f"Census: {len(sites)} sites")
        header = f"{len(sites)} sites: {old}"
        if new != old:
            header += f" &rarr; {new}"
        writer.start_section(header)
        for site in sites:
            old, new = site.latest_courses, site.current_courses
            tags = []
            if new is None:
                tags.append(f"<span class='tag none'>None</span>")
                new_text = ""
            else:
                new_text = f" &rarr; {new}"
                if abs(new - old) > 10 and not (0.5 >= old/new >= 1.5):
                    tags.append(f"<span class='tag drastic'>Drastic</span>")
            if site.time > 5:
                tags.append(f"<span class='tag slow'>{site.time:.1f}s</span>")
            writer.start_section(f"<a class='url' href='{site.url}'>{site.url}</a>: {old}{new_text} {''.join(tags)}")
            for strategy, tb in site.tried:
                if tb is not None:
                    lines = tb.splitlines()
                    if len(lines) > 1:
                        line = tb.splitlines()[-1][:100]
                        writer.start_section(f"<span class='strategy'>{strategy}:</span> {escape(line)}")
                        writer.write("""<pre class="stdout">""")
                        writer.write(escape(tb))
                        writer.write("""</pre>""")
                        writer.end_section()
                    else:
                        writer.write(f"<p>{strategy}: {lines[0]}")
                else:
                    writer.write(f"<p>{strategy}: worked</p>")
            writer.end_section()
        writer.end_section()

        total_course_ids = sum(len(sites) for sites in all_courses.values())
        writer.start_section(f"<p>Course IDs: {total_course_ids}</p>")
        all_courses_items = sorted(all_courses.items())
        all_courses_items = sorted(all_courses_items, key=lambda item: len(item[1]), reverse=True)
        for course_id, sites in all_courses_items:
            writer.start_section(f"{course_id}: {len(sites)}")
            for site in sites:
                writer.write(f"<p><a class='url' href='{site.url}'>{site.url}</a></p>")
            writer.end_section()
        writer.end_section()

        shared_orgs = [(org, sites) for org, sites in all_orgs.items() if len(sites) > 1]
        writer.start_section(f"<p>Shared orgs: {len(shared_orgs)}</p>")
        for org, sites in sorted(shared_orgs):
            writer.start_section(f"{org}: {len(sites)}")
            for site in sites:
                writer.write(f"<p><a class='url' href='{site.url}'>{site.url}</a></p>")
            writer.end_section()
        writer.end_section()

def json_update(sites, all_courses, include_overcount=False):
    data = {}

    site_updates = {
        s.url: {
            'old_course_count': s.latest_courses,
            'course_count': s.current_courses if s.current_courses is not None else s.latest_courses,
            'is_gone': s.is_gone_now,
        }
        for s in sites if s.should_update()
    }
    data['sites'] = site_updates

    if include_overcount:
        data['overcount'] = sum(len(s) - 1 for s in all_courses.values())

    with open(UPDATE_JSON, "w") as update_json:
        json.dump(data, update_json, indent=4)


def login(site, session):
    login_url = urllib.parse.urljoin(site, "/login/")
    resp = session.get(login_url)
    resp.raise_for_status()
    m = re.search(r"name='csrfmiddlewaretoken' value='([^']+)'", resp.text)
    if m:
        csrftoken = m.group(1)
    else:
        raise Exception(f"No CSRF token found from {login_url}")
    resp = session.post(login_url, data={'username': username, 'password': password, 'csrfmiddlewaretoken': csrftoken})
    if resp.status_code not in [200, 404]:
        resp.raise_for_status()

@cli.command()
@click.argument('site', default=STATS_SITE)
def getcsv(site):
    with requests.Session() as s:
        login(site, s)
        csv_url = urllib.parse.urljoin(site, "/sites/csv/?complete=1")
        resp = s.get(csv_url)
        content = resp.content
        with open(SITES_CSV, "wb") as csv_file:
            csv_file.write(content)
        lines = content.splitlines()
        print(f"Wrote {len(lines)-1} sites to {SITES_CSV}")


@cli.command()
@click.argument('site', default=STATS_SITE)
def post(site):
    """Post updated numbers to the stats-collecting site."""
    with open(UPDATE_JSON) as f:
        data = f.read()

    with requests.Session() as s:
        login(site, s)
        bulk_url = urllib.parse.urljoin(site, "/sites/bulk/")
        resp = s.post(bulk_url, data=data)
        print(resp.text)


if __name__ == '__main__':
    cli()
