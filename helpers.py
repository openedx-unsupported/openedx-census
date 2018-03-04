"""Helpers for picking apart web data."""

import lxml
import lxml.html
import parse


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

def parse_text(pattern, text):
    """Parse a pattern from https://pypi.python.org/pypi/parse

    Returns the parse.Result object.

    Raises an exception if no match.
    """
    result = parse.parse(pattern, text.strip())
    if not result:
        raise ValueError(f"Couldn't apply pattern {pattern!r} to {text!r}")
    return result
