"""Visit Open edX sites and count their courses."""

import asyncio
import csv
import logging
import pprint
import re

import aiohttp
import attr
import click

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

    async def text_from_url(self, url, came_from=None, method='get', save=False):
        headers = {}
        if came_from:
            async with self.session.get(came_from) as resp:
                real_url = str(resp.url)
                x = await resp.read()
            cookies = self.session.cookie_jar.filter_cookies(url)
            if 'csrftoken' in cookies:
                headers['X-CSRFToken'] = cookies['csrftoken'].value

            headers['Referer'] = real_url

        async with getattr(self.session, method)(url, headers=headers) as response:
            text = await response.read()

        if save:
            with open("save.html", "wb") as f:
                f.write(text)
        return text

    async def real_url(self, url):
        async with self.session.get(url) as resp:
            return str(resp.url)


MAX_CLIENTS = 200
USER_AGENT = "Open edX census-taker. Tell us about your site: oscm+census@edx.org"


async def fetch(site, session):
    try:
        parser = find_site_function(site.url)
        site.current_courses = await parser(site, session)
        print(".", end='', flush=True)
        return True
    except Exception as exc:
        #log.exception(f"Couldn't fetch {site.url}")
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
    # Some exceptions go to stderr and then to my except clause? Shut up.
    loop.set_exception_handler(lambda loop, context: None)
    loop.run_until_complete(future)

def read_sites(csv_file):
    with open(csv_file) as f:
        next(f)
        for row in csv.reader(f):
            url = row[1].strip().strip("/")
            courses = int(row[2] or 0)
            if not url.startswith("http"):
                url = "http://" + url
            yield Site(url, courses)

@click.command(help=__doc__)
@click.option('--min', type=int, default=100)
@click.argument('site_patterns', nargs=-1)
def main(min, site_patterns):
    sites = list(read_sites("sites.csv"))
    sites = [s for s in sites if s.latest_courses >= min]
    if site_patterns:
        sites = [s for s in sites if any(re.search(p, s.url) for p in site_patterns)]
    print(f"{len(sites)} sites")

    get_urls(sites)

    for site in sorted(sites, key=lambda s: s.latest_courses, reverse=True):
        print(site)

    old = new = 0
    for site in sites:
        if site.current_courses:
            old += site.latest_courses
            new += site.current_courses
    print(f"Found courses went from {old} to {new}")

if __name__ == '__main__':
    main()
