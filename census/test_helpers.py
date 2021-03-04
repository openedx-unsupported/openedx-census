import pytest

from census.helpers import domain_from_url, is_chaff_domain, emails_in_text

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

@pytest.mark.parametrize("text, emails", [
    (b"hello ned@edy.org there", [b"ned@edy.org"]),
    (b"hello foo/fancybox@3.5.7/bar there", []),
    (b"my email is ned@edy.org or ned2@edy.org. Write me!",
        [b"ned@edy.org", b"ned2@edy.org"]),
])
def test_emails_in_text(text, emails):
    assert list(emails_in_text(text)) == emails
