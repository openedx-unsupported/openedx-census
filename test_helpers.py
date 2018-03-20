import pytest

from helpers import domain_from_url, is_chaff_domain

@pytest.mark.parametrize("domain, url", [
    ("http://nedbatchelder.com/hello", "nedbatchelder.com"),
    ("https://nedbatchelder.com", "nedbatchelder.com"),
    ("nedbatchelder.com", "nedbatchelder.com"),
    ("http://hello.nedbatchelder.com/", "hello.nedbatchelder.com"),
])
def test_domain_from_url(domain, url):
    assert domain_from_url(domain) == url

@pytest.mark.parametrize("domain, is_chaff", [
    ("nedbatchelder.com", False),
    ("fun.fun-mooc.com", False),
    ("test.edx.org", True),
    ("sandbox-hello.edx.org", True),
    ("sandbox23.somewhere.org", True),
])
def test_is_chaff_domain(domain, is_chaff):
    assert is_chaff_domain(domain) == is_chaff
