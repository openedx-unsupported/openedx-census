"""Helpers for making reports."""

import collections

from census.helpers import domain_from_url
from census.settings import ALIASES_TXT, SITES_CSV
from census.sites import read_sites_csv, HashedSite


def sort_sites(sites):
    """Sort sites in size-decreasing order."""
    sites = sorted(sites, key=lambda s: s.url.split(".")[::-1])
    sites = sorted(sites, key=lambda s: s.current_courses or s.latest_courses, reverse=True)
    return sites


def get_known_domains():
    known_domains = {domain_from_url(site.url) for site in read_sites_csv(SITES_CSV)}
    with open(ALIASES_TXT) as aliases:
        known_domains.update(domain_from_url(line.strip()) for line in aliases)
    return known_domains


def hash_sites_together(sites, known_domains, only_new=False):
    hashed_sites_by_fp = collections.defaultdict(HashedSite)
    for site in sites:
        fp = site.fingerprint or site.url
        hashed_site = hashed_sites_by_fp[fp]
        hashed_site.fingerprint = fp
        hashed_site.version = site.version
        hashed_site.sites.append(site)

    hashed_sites = list(hashed_sites_by_fp.values())

    for hashed_site in hashed_sites:
        if hashed_site.all_chaff():
            hashed_site.is_new = False
        else:
            hashed_site.is_new = not hashed_site.any_known(known_domains)

    if only_new:
        new_hashed_sites = []
        for hashed_site in hashed_sites:
            if hashed_site.is_new:
                new_hashed_sites.append(hashed_site)
        hashed_sites = new_hashed_sites

    hashed_sites = sorted(hashed_sites, key=lambda hs: hs.current_courses() or 0, reverse=True)

    return hashed_sites
