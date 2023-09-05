"""Associate functions with url patterns."""

import re

SITE_PATTERNS = []

def matches(suffix, *args, **kwargs):
    """Decorator for a parser to apply to any url that ends with the suffix."""
    def _decorator(func):
        pattern = re.compile(r"\b" + re.escape(suffix) + r"$")
        SITE_PATTERNS.append((pattern, func, args, kwargs))
        return func
    return _decorator

def matches_any(func):
    """Decorator for a parser that applies to any url at all."""
    SITE_PATTERNS.append((None, func, (), {}))
    return func

def find_site_functions(url):
    """Yield func, args, kwargs, custom_or_not."""
    for pattern, func, args, kwargs in SITE_PATTERNS:
        if pattern is None or pattern.search(url):
            yield func, args, kwargs, (pattern is not None)
