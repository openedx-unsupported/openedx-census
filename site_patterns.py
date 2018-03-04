"""Associate functions with url patterns."""

import re

SITE_PATTERNS = []

def matches(suffix):
    """Decorator for a parser to apply to any url that ends with the suffix."""
    def _decorator(func):
        SITE_PATTERNS.append((re.compile(r"\b" + re.escape(suffix) + r"$"), func))
        return func
    return _decorator

def matches_any(func):
    """Decorator for a parser that applies to any url at all."""
    SITE_PATTERNS.append((re.compile(r"."), func))
    return func

def find_site_functions(url):
    for pattern, func in SITE_PATTERNS:
        if pattern.search(url):
            yield func
