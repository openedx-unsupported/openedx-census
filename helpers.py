"""Helpers for picking apart web data."""

import urllib.parse

import lxml
import lxml.html
import parse


def site_url(site, rel_url):
    """Compose an absolute URL from a site and a relative url."""
    url = urllib.parse.urljoin(site.url, rel_url)
    return url

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

def element_by_css(html, css):
    elts = elements_by_css(html, css)
    if len(elts) > 1:
        raise ValueError(f"Found {len(elts)} that matched {css!r}")
    if len(elts) == 0:
        raise ValueError(f"Found nothing that matched {css!r}")
    return elts[0]

def parse_text(pattern, text):
    """Parse a pattern from https://pypi.python.org/pypi/parse

    Returns the parse.Result object.

    Raises an exception if no match.
    """
    result = parse.parse(pattern, text.strip())
    if not result:
        raise ValueError(f"Couldn't apply pattern {pattern!r} to {text!r}")
    return result
