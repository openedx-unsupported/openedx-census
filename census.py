import asyncio
import csv
import json
import logging
import pprint
import re

import aiohttp
import attr
import lxml
import lxml.html

log = logging.getLogger(__name__)

@attr.s
class Site:
    url = attr.ib()
    latest_courses = attr.ib()
    current_courses = attr.ib(default=None)
    error = attr.ib(default=None)


SITE_PATTERNS = []

def parse_site(pattern):
    def _decorator(func):
        SITE_PATTERNS.append((pattern, func))
        return func
    return _decorator

class SmartSession:
    def __init__(self, session):
        self.session = session

    def __getattr__(self, name):
        return getattr(self.session, name)

    async def text_from_url(self, url, came_from=None, method='get'):
        headers = {}
        if came_from:
            async with self.session.get(came_from) as resp:
                x = await resp.read()
            cookies = self.session.cookie_jar.filter_cookies(url)
            if 'csrftoken' in cookies:
                headers['X-CSRFToken'] = cookies['csrftoken'].value

            headers['Referer'] = came_from

        async with getattr(self.session, method)(url, headers=headers) as response:
            return await response.read()


def elements_by_xpath(html, xpath):
    parser = lxml.etree.HTMLParser()
    tree = lxml.etree.fromstring(html, parser)
    elts = tree.xpath(xpath)
    return elts

def elements_by_css(html, css):
    parser = lxml.etree.HTMLParser()
    tree = lxml.etree.fromstring(html, parser)
    elts = tree.cssselect(css)
    return elts


# XuetangX: add up courses by institution.
@parse_site(r"www\.xuetangx\.com$")
async def parser(site, session):
    url = "http://www.xuetangx.com/partners"
    text = await session.text_from_url(url)
    section = elements_by_xpath(text, "/html/body/article[1]/section")
    assert len(section) == 1
    assert section[0].xpath("h2")[0].text == "开课院校"
    li = section[0].xpath("ul/li/a/div[2]/p[1]")
    courses = 0
    for l in li:
        suffix = "门课程"
        text = l.text
        assert text.endswith(suffix)
        courses += int(text[:-len(suffix)])
    return courses

# FUN has an api that returns a count.
@parse_site(r"france-universite-numerique-mooc\.fr$")
async def parser(site, session):
    url = "https://www.fun-mooc.fr/fun/api/courses/?rpp=50&page=1"
    text = await session.text_from_url(url)
    data = json.loads(text)
    return data['count']

@parse_site(r"courses.openedu.tw$")
async def parser(site, session):
    url = "https://www.openedu.tw/rest/courses/query"
    text = await session.text_from_url(url)
    data = json.loads(text)
    return len(data)

@parse_site(r"courses.zsmu.edu.ua")
@parse_site(r"lms.mitx.mit.edu")
async def front_page_full_of_tiles(site, session):
    text = await session.text_from_url(site.url)
    li = elements_by_css(text, "li.courses-listing-item")
    return len(li)

@parse_site(r"openedu.ru$")
async def parser(site, session):
    url = "https://openedu.ru/course/"
    text = await session.text_from_url(url)
    count = elements_by_css(text, "span#courses-found")[0]
    assert count.text.endswith(" курс")
    return int(count.text.split()[0])

@parse_site(r"puroom.net$")
async def parser(site, session):
    url1 = 'https://lms.puroom.net/courses'
    url = "https://lms.puroom.net/search/course_discovery/"
    text = await session.text_from_url(url, came_from=url1, method='post')
    data = json.loads(text)
    count = data["facets"]["emonitoring_course"]["total"]
    return count

async def default_parser(site, session):
    text = await session.text_from_url(site.url)
    return len(text) * 1000


MAX_CLIENTS = 100
USER_AGENT = "Open edX census-taker. Tell us about your site: oscm+census@edx.org"


async def fetch(site, session):
    try:
        for pattern, parser in SITE_PATTERNS:
            if re.search(pattern, site.url):
                site.current_courses = await parser(site, session)
                break
        else:
            site.current_courses = await default_parser(site, session)
        print(".", end='', flush=True)
        return True
    except Exception as exc:
        log.exception(f"Couldn't fetch {site.url}")
        site.error = str(exc)
        print("X", end='', flush=True)
        return False

async def throttled_fetch(site, session, sem):
    async with sem:
        return await fetch(site, session)

async def run(sites):
    tasks = []
    sem = asyncio.Semaphore(MAX_CLIENTS)

    headers = {
        'User-Agent': USER_AGENT,
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        smart = SmartSession(session)
        for site in sites:
            task = asyncio.ensure_future(throttled_fetch(site, smart, sem))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        print()

def get_urls(sites):
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(run(sites))
    loop.run_until_complete(future)
    for site in sorted(sites, key=lambda s: s.latest_courses, reverse=True):
        print(site)

def read_sites(csv_file):
    with open(csv_file) as f:
        next(f)
        for row in csv.reader(f):
            url = row[1].strip().strip("/")
            courses = int(row[2] or 0)
            if courses < 100:
                continue
            if not url.startswith("http"):
                url = "http://" + url
            yield Site(url, courses)

if __name__ == '__main__':
    sites = list(read_sites("sites.csv"))
    print(f"{len(sites)} sites")
    get_urls(sites)
