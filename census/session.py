import asyncio
import itertools
import logging
import os
import re

import aiohttp
import async_timeout
from asyncio_extras.contextmanager import async_contextmanager

from census.helpers import HttpError


log = logging.getLogger(__name__)

class SmartSession:
    def __init__(self, sem, timeout=20, headers=None, save=False, saver=None, **kwargs):
        self.sem = sem
        self.timeout = timeout
        self.kwargs = kwargs
        self.session = aiohttp.ClientSession(headers=headers or {}, raise_for_status=True)
        self.save = save
        self.saver = saver

    async def __aenter__(self):
        await self.session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.__aexit__(exc_type, exc_val, exc_tb)

    def __getattr__(self, name):
        return getattr(self.session, name)

    @async_contextmanager
    async def request(self, url, method="get", **kwargs):
        """How we like to make HTTP requests."""
        async with self.sem:
            log.debug("%s %s", method.upper(), url)
            with async_timeout.timeout(self.timeout):
                try:
                    async with self.session.request(method, url, **self.kwargs, **kwargs) as response:
                        yield response
                except aiohttp.ClientError as exc:
                    code = getattr(exc, 'code', str(exc))
                    raise HttpError(f"{code} {method} {url}")

    async def text_from_url(self, url, came_from=None, method='get', data=None, save=False):
        headers = {}
        if came_from:
            async with self.request(came_from) as resp:
                real_url = str(resp.url)
                from_text = await resp.read()
            if self.saver and (save or self.save):
                self.saver(url, from_text, resp)
            cookies = self.session.cookie_jar.filter_cookies(url)
            if 'csrftoken' in cookies:
                headers['X-CSRFToken'] = cookies['csrftoken'].value

            headers['Referer'] = real_url

        async with self.request(url, method, headers=headers, data=data) as response:
            try:
                text = await response.read()
            except aiohttp.ClientError as exc:
                code = getattr(exc, 'code', str(exc))
                raise HttpError(f"{code} {method} {url}")

        if self.saver and (save or self.save):
            self.saver(url, text, response)
        return text

    async def real_url(self, url):
        async with self.request(url) as resp:
            return str(resp.url)


class Saver:
    def __init__(self, dir="save"):
        self.save_numbers = itertools.count()
        self.dir = dir

    def save(self, url, text, response):
        os.makedirs(self.dir, exist_ok=True)
        num = next(self.save_numbers)
        ext = re.split(r"[+/]", response.content_type)[-1]
        save_name = f"{num:03d}.{ext}"
        with open(os.path.join(self.dir, "index.txt"), "a") as idx:
            print(f"{save_name}: {response.method} {url} ({response.status})", file=idx)
        with open(os.path.join(self.dir, save_name), "wb") as f:
            f.write(text)


class SessionFactory:
    def __init__(self, max_requests=10, **kwargs):
        self.sem = asyncio.Semaphore(max_requests)
        self.session_kwargs = kwargs

    def new(self, **kwargs):
        save = bool(int(os.environ.get('SAVE', 0)))
        return SmartSession(self.sem, save=save, saver=Saver().save, **self.session_kwargs, **kwargs)
