"""Parsers for specific sites."""

import collections
import datetime
import itertools
import json
import re
import urllib.parse

from census.helpers import (
    site_url,
    parse_text,
    element_by_css, elements_by_css, elements_by_xpath,
    GotZero,
)
from census.site_patterns import matches, matches_any

# FUN has an api that returns a count.
@matches("fun-mooc.fr", "/fun/api/courses/?rpp=50&page=1", "count")
@matches("learn.in.th", "/main/frontend/ListCourses/listSearch/1", "all_row")
@matches("develop.com", "/wp-json/dcom-blocks/v1/courses/", "total")
async def json_total_value_parser(site, session, rel_url, key):
    url = site_url(site, rel_url)
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    data = json.loads(text)
    return data[key]

@matches("://openedu.tw")
async def openedu_tw_parser(site, session):
    url = "https://www.openedu.tw/rest/courses/query"
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    data = json.loads(text)
    return len(data)

@matches("openedu.ru")
async def openedu_ru_parser(site, session):
    url = site_url(site, "/course/")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    count = element_by_css(text, "span#courses-found")
    assert " кур" in count.text
    return int(count.text.split()[0])

@matches("gacco.org")
async def gacco_parser(site, session):
    url = site_url(site, "/data/course/gacco_list.json")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    data = json.loads(text)
    count = len(data["opened_courses"])

    url = site_url(site, "/data/course/gacco_archive.json")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    data = json.loads(text)
    count += len(data["archived_courses"])
    return count

# Lots of sites have customized CSS for their courses
@matches("doroob.sa", "/ar/individuals/elearning/", ".courses-listing-item")
@matches("labster.com", "/simulations/", ".md-simulation-card")
@matches("wasserx.com", "/courses/", "li.course-item")
@matches("modernstates.org", "/course/", "#course-card-grid .course-card")
@matches("juxhub.com", "/course.html", ".courses-thumb")
@matches("frdelpinoenred.com", "/todos-los-cursos/", ".course-item")
@matches("erevuka.org", "/courses/", "#courses-wrapper .single-course-wrapper")
@matches("xpro.mit.edu", "/catalog/", "#all .catalog-card")
@matches("lge.smartlearn.io", "/", "article")
@matches("edx.gchumanrights.org", "/courses/", ".course_info")
async def count_elements_parser(site, session, rel_url, css):
    url = site_url(site, rel_url)
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    elts = elements_by_css(text, css)
    count = len(elts)
    return count

@matches("millionlights.org")
async def millionlights_parser(site, session):
    url = site_url(site, "/Course/AllCourses")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    # Find the language-faceted results, and add up their parenthesized
    # numbers.
    elts = elements_by_xpath(text, "//a[contains(text(), 'English (')]/ancestor::ul//a")
    count = 0
    for elt in elts:
        result = parse_text("{} ({:d})", elt.text)
        count += result[1]
    return count

@matches("enlightme.net")
async def enlightme_parser(site, session):
    url = site_url(site, "/courses/")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    elt = element_by_css(text, ".course-index span")
    result = parse_text("Showing 1-10 of {:d} results", elt.text)
    return result[0]

@matches("skills.med.hku.hk")
async def hku_hk_parser(site, session):
    url = site_url(site, "/mbbs_admin/public/downloadMbbsJsonFile")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    data = json.loads(text)
    count = len(data)
    return count

@matches("skillvideo.nursing.hku.hk")
async def hku_nursing_parser(site, session):
    url = site_url(site, "/nurs_admin/public/downloadNursJsonFile")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    data = json.loads(text)
    count = len(data)
    return count

@matches("learning.hku.hk")
async def learning_hku_parser(site, session):
    url = site_url(site, "/catalog/all-courses/")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    elt = element_by_css(text, "li#course-all span")
    count = int(elt.text)
    return count

@matches("campus.gov.il")
async def campus_il_parser(site, session):
    url = site_url(site, "/course")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    elt = element_by_css(text, "span#add-sum-course")
    count = int(elt.text)
    return count

@matches("iitbombayx.in")
async def iitbombayx_parser(site, session):
    url = site_url(site, "/courses")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    elts = elements_by_css(text, "#block-timeline-2 .facet-item__count")
    count = 0
    for elt in elts:
        count += int(elt.text.strip("()"))
    return count

@matches("edraak.org")
async def edraak_org_parser(site, session):
    url = site_url(site, "/en/courses/")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    elts = elements_by_css(text, "aside.all-courses div.course span")
    count = 0
    for elt in elts:
        count += int(elt.text.strip(" ()"))
    return count

@matches("edcast.org")
async def edcast_org_parser(site, session):
    url = site_url(site, "/search")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    h4 = element_by_css(text, ".search-navigation-row h4")
    result = parse_text("All Courses ({:d} matches)", h4.text)
    return result[0]

@matches("cognitiveclass.ai")
@matches("bigdatauniversity.com.cn")
async def cognitiveclass_parser(site, session):
    url = site_url(site, "/courses")
    count = 0
    while True:
        text = await session.text_from_url(url)
        site.add_to_fingerprint(text)
        elts = elements_by_css(text, "article.course.card")
        count += len(elts)
        # Find the a element with '>' as the text, get its href.
        next_href = elements_by_xpath(text, "//a/span[text() = '>']/../@href")
        if not next_href:
            break
        assert len(next_href) == 1
        url = urllib.parse.urljoin(url, next_href[0])
    return count

@matches("entuze.com")
async def entuze_parser(site, session):
    url = site_url(site, "/course_packages/")
    text = await session.text_from_url(url)
    site.add_to_fingerprint(text)
    elt = element_by_css(text, "div#discovery-message")
    result = parse_text("Viewing {:d} courses", elt.text)
    return result[0]

@matches("eso.org.br")
async def prefer_tiles(site, session):
    return await courses_page_full_of_tiles(site, session)

@matches("gotoclass.ir")
async def gotoclass_parser(site, session):
    url = site_url(site, "/courses/")
    count = 0
    while True:
        text = await session.text_from_url(url)
        site.add_to_fingerprint(text)
        elts = elements_by_css(text, "div.course-block")
        count += len(elts)
        next_a = elements_by_css(text, "a.next.page-numbers")
        if not next_a:
            break
        assert len(next_a) == 1
        url = urllib.parse.urljoin(url, next_a[0].get('href'))
    return count

@matches("openu.kz")
async def openu_kz_parser(site, session):
    text = await session.text_from_url(site.url)
    site.add_to_fingerprint(text)
    stat_elt = elements_by_css(text, ".statistics-block .statistics-block__value")[0]
    count = int(stat_elt.text)
    return count

@matches("academy.numfocus.org")
async def numfocus_parser(site, session):
    urls = collections.deque()
    urls.append(site.url)
    count = 0
    while urls:
        url = urls.popleft()
        text = await session.text_from_url(url)
        site.add_to_fingerprint(text)

        # Look for courses.
        tiles = elements_by_css(text, ".course-rec-3")
        count += len(tiles)

        # Look for further pages that are or have courses.
        subs = elements_by_css(text, ".et_pb_blurb_content a")
        hrefs = set(sub.get("href") for sub in subs)
        for href in hrefs:
            if "/about-course/" in href:
                count += 1
            else:
                urls.append(href)

    return count

@matches("www.edx.org")
async def edx_org_parser(site, session):
    url = site_url(site, "/api/v1/catalog/search?page=1&page_size=200")
    count = 0
    while True:
        text = await session.text_from_url(url)
        site.add_to_fingerprint(text)
        data = json.loads(text)
        objs = data['objects']['results']
        count += len(objs)
        for obj in objs:
            course_id = obj.get('key')
            if course_id:
                site.course_ids[course_id] += 1
        url = data['objects'].get('next')
        if not url:
            break
    return count

# I would like to have a way to "symlink" one site to another, and have the
# full parsing machinery operate on that other site, but that got complicated.
# This is a quick way to get the same effect.
@matches("edx.hospitalmoinhos.org.br", "http://lms.hospitalmoinhos.org.br/")
async def count_other_site_tiles(site, session, other_url):
    return await count_tiles(other_url, site, session)


# Generic parsers

def filter_by_date(elts, cutoff):
    """Filter elements based on a <time> element."""
    ok = []
    for elt in elts:
        time_spec = elt.xpath(".//time/@data-datetime")
        if time_spec and time_spec[0] > cutoff:
            continue
        ok.append(elt)
    return ok

OPENEDX_SNIPS = [b"open edx", b"openedx", b"edx.org", b"edx-theme-codebase"]

async def count_tiles(url, site, session):
    text = await session.text_from_url(url)
    elts = elements_by_css(text, ".courses ul.courses-listing > li")
    count = len(elts)
    if count == 0:
        elts = elements_by_css(text, ".courses-listing-item")
        count = len(elts)
        if count == 0:
            # No courses, but do we see any indication of it being open edx?
            if any(snip in text.lower() for snip in OPENEDX_SNIPS):
                site.is_openedx = True
            raise GotZero("No .courses-listing-item's")

    soon = datetime.datetime.now() + datetime.timedelta(days=365)
    elts = filter_by_date(elts, soon.isoformat())
    count = len(elts)

    # Try to get the course ids also!
    try:
        for elt in elts:
            course_id = elt.xpath("article/@id")[0]
            site.course_ids[course_id] += 1
    except Exception:
        pass
    site.add_to_fingerprint(text)
    return count

@matches_any
async def edx_search_post(site, session):
    real_url = await session.real_url(site.url)
    url0 = urllib.parse.urljoin(real_url, '/courses')
    # Note: the URL says course_discovery, but this is not the Course Discovery
    # app, it routes through to edx-search.
    url = urllib.parse.urljoin(real_url, '/search/course_discovery/')
    search_params = {
        'exclude_ended_courses': 'true',
        'only_can_enroll_courses': 'false',
        'page_size': 100,
        }
    count = 0
    soon = (datetime.datetime.now() + datetime.timedelta(days=365)).isoformat()
    for search_params['page_index'] in itertools.count():
        text = await session.text_from_url(url, came_from=url0, method='post', data=search_params)
        try:
            data = json.loads(text)
        except Exception:
            raise Exception(f"Couldn't parse result from json: {text[:100]!r}")
        if data["total"] == 0:
            raise GotZero("data[total] is zero")
        if not data["results"]:
            # We've paginated through all the results.
            break
        try:
            for course in data["results"]:
                site.course_ids[course["_id"]] += 1
                start = course["data"]["start"]
                if start < soon:
                    count += 1
        except Exception:
            pass
        # The JSON has a "took" key, the time to respond, which we don't
        # want in the fingerprint.
        del data['took']
        site.add_to_fingerprint(json.dumps(data, sort_keys=True).encode('utf8'))
        url0 = None
    return count

@matches_any
async def courses_page_full_of_tiles(site, session):
    url = site_url(site, "/courses")
    return await count_tiles(url, site, session)

@matches_any
async def home_page_full_of_tiles(site, session):
    return await count_tiles(site.url, site, session)
