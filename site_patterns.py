"""Associate functions with url patterns."""

import re

SITE_PATTERNS = []

def matches(pattern):
    def _decorator(func):
        SITE_PATTERNS.append((re.compile(r"\b" + pattern), func))
        return func
    return _decorator

def find_site_functions(url):
    for pattern, func in SITE_PATTERNS:
        if pattern.search(url):
            yield func
