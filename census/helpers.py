"""Helpers for picking apart web data."""

import hashlib
import re
import urllib.parse

import lxml
import lxml.html
import parse


class ScrapeFail(Exception):
    """Any controlled failure of scraping."""
    pass

class GotZero(ScrapeFail):
    """Raised when we couldn't find the info we want."""
    pass

class HttpError(ScrapeFail):
    """Raised to nicely handle HTTP errors."""
    pass


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
        elt_text = "; ".join(lxml.etree.tostring(elt, encoding='unicode').strip() for elt in elts)
        raise ValueError(f"Found {len(elts)} that matched {css!r}: {elt_text}")
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

def fingerprint(text):
    """Return a hex string that fingerprints `text`."""
    return hashlib.sha1(text).hexdigest()

def domain_from_url(url):
    return urllib.parse.urlparse(url).netloc or url

def is_known(site, known_domains):
    domain = domain_from_url(site.url)
    for prefix in ['', 'www.']:
        dom = domain
        if domain.startswith(prefix):
            dom = domain[len(prefix):]
        if dom in known_domains:
            return True
    return False

CHAFF_WORDS = set("""
    stage staging preview demo dev sandbox test loadtest qa
    trafficmanager cloudapp
    formation
    aspen birch cypress dogwood eucalyptus ficus ginkgo hawthorn ironwood juniper koa
    """.split())

def is_chaff_domain(domain):
    """Is this domain something we should ignore?"""
    parts = re.split(r"[.-]", domain)
    return any(part.rstrip("0123456789") in CHAFF_WORDS for part in parts)

VERSION_SNIPS = [
    ('ginkgo', b'<a class="nav-skip sr-only sr-only-focusable" href="#main">'),
    ('ficus', b'DateUtilFactory.transform(iterationKey=".localized_datetime");'),
    ('eucalytpus', b'<a class="nav-skip" href="#main">'),
    ('dogwood', b'<a class="nav-skip" href="#content">'),
    ('cypress', b'<script type="text/javascript" src="/jsi18n/"></script>'),
    ('birch', b'<header class="global '),
]

def sniff_version(text):
    meta = b'<meta name="openedx-release-line" content="'
    if meta in text:
        release = text.partition(meta)[2].partition(b'"')[0]
        return release.decode()
    for version, snip in VERSION_SNIPS:
        if snip in text:
            return version

TAG_SNIPS = [
    ('bitnami', b'<div id="bitnami-banner" '),
    ('edunext', b' href="https://www.edunext.co" '),
    ('overlimit', b'This site is temporarily restricted because the account limits have been reached.'),    # eduNEXT, overlimit.
    ('appsembler', b' href="https://www.appsembler.com" '),
    ('raccoongang', b' href="https://raccoongang.com" '),
    ('opencraft', b'static/simple-theme/images/logo.85cf838f1fea.png'),
    ('ibl', b'static/poweredibl.png"'),
    ('tutor', b'docs.tutor.overhang.io'),
    ('indigo', b'type="image/x-icon" href="/static/indigo3/images/favicon'),
    ('aulasneo', b'aulasneo'),
]

TAG_URL_ENDS = [
    ('ibm', 'openedx.site'),
    ('edunext', 'edunext.io'),
    ('opencraft', 'opencraft.hosting'),
    ('appsembler', 'tahoe.appsembler.com'),
    ('raccoongang', 'raccoongang.com'),
    ('ibl', 'iblstudios.com'),
    ('ibl', 'ibleducation.com'),
    ('aulasneo', 'aulasneo.com'),
]

def sniff_tags(url, text):
    for tag, snip in TAG_SNIPS:
        if snip in text:
            yield tag
    for tag, end in TAG_URL_ENDS:
        if url.endswith(end):
            yield tag
