import asyncio
import itertools
import logging
import os

import aiohttp
import async_timeout

from helpers import HttpError


log = logging.getLogger(__name__)

REQUEST_KWARGS = dict(verify_ssl=False)

class SmartSession:
    def __init__(self, max_requests=30, timeout=20, headers=None):
        self.sem = asyncio.Semaphore(max_requests)
        self.timeout = timeout
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

    async def request(self, url, method="get", **kwargs):
        """How we like to make HTTP requests."""
        async with self.sem:
            log.debug("%s %s", method.upper(), url)
            with async_timeout.timeout(self.timeout):
                try:
                    async with getattr(self.session, method)(url, **kwargs, **REQUEST_KWARGS) as response:
                        return response
                except aiohttp.ClientResponseError as exc:
                    raise HttpError(f"{exc.code} {exc.request_info.method} {exc.request_info.url}")

    async def text_from_url(self, url, came_from=None, method='get', data=None, save=False):
        headers = {}
        if came_from:
            resp = await self.request(came_from)
            real_url = str(resp.url)
            x = await resp.read()
            cookies = self.session.cookie_jar.filter_cookies(url)
            if 'csrftoken' in cookies:
                headers['X-CSRFToken'] = cookies['csrftoken'].value

            headers['Referer'] = real_url

        response = await self.request(url, method, headers=headers, data=data)
        text = await response.read()

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
        resp = await self.request(url)
        return str(resp.url)



