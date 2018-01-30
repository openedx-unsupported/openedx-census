import asyncio
import csv
import logging
import pprint

import aiohttp
import attr

from site_patterns import find_site_function

# We don't use anything from this module, it just registers all the parsers.
import sites


log = logging.getLogger(__name__)

@attr.s
class Site:
    url = attr.ib()
    latest_courses = attr.ib()
    current_courses = attr.ib(default=None)
    error = attr.ib(default=None)


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


MAX_CLIENTS = 100
USER_AGENT = "Open edX census-taker. Tell us about your site: oscm+census@edx.org"


async def fetch(site, session):
    try:
        parser = find_site_function(site.url)
        site.current_courses = await parser(site, session)
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
