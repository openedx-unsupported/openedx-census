import asyncio
import itertools
import logging
import os
import re

import aiohttp
import async_timeout
from asyncio_extras.contextmanager import async_contextmanager

from helpers import HttpError


log = logging.getLogger(__name__)

class SmartSession:
    def __init__(self, sem, timeout=20, headers=None, **kwargs):
        self.sem = sem
        self.timeout = timeout
        self.kwargs = kwargs
        self.session = aiohttp.ClientSession(headers=headers or {}, raise_for_status=True)
        self.save_numbers = itertools.count()
        self.save = bool(int(os.environ.get('SAVE', 0)))

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
                x = await resp.read()
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

        if save or self.save:
            num = next(self.save_numbers)
            ext = re.split(r"[+/]", response.content_type)[-1]
            save_name = f"save_{num:03d}.{ext}"
            with open(f"save_index.txt", "a") as idx:
                print(f"{save_name}: {url} ({response.status})", file=idx)
            with open(save_name, "wb") as f:
                f.write(text)
        return text

    async def real_url(self, url):
        async with self.request(url) as resp:
            return str(resp.url)

class SessionFactory:
    def __init__(self, max_requests=10, **kwargs):
        self.sem = asyncio.Semaphore(max_requests)
        self.session_kwargs = kwargs

    def new(self, **kwargs):
        return SmartSession(self.sem, **self.session_kwargs, **kwargs)
