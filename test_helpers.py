import pytest

from helpers import is_chaff_domain

@pytest.mark.parametrize("domain, is_chaff", [
    ("nedbatchelder.com", False),
    ("fun.fun-mooc.com", False),
    ("test.edx.org", True),
    ("sandbox-hello.edx.org", True),
    ("sandbox23.somewhere.org", True),
])
def test_is_chaff_domain(domain, is_chaff):
    assert is_chaff_domain(domain) == is_chaff
