"""Parsers for specific sites."""

import datetime
import json
import re
import urllib.parse

from helpers import element_by_css, elements_by_css, elements_by_xpath, parse_text
from site_patterns import matches, matches_any

# XuetangX: add up courses by institution.
@matches("www.xuetangx.com")
async def xuetang_parser(site, session):
    url = "http://www.xuetangx.com/partners"
    text = await session.text_from_url(url)
    section = elements_by_xpath(text, "/html/body/article[1]/section")
    assert len(section) == 1
    assert section[0].xpath("h2")[0].text == "开课院校"
    li = section[0].xpath("ul/li/a/div[2]/p[1]")
    courses = 0
    for l in li:
        suffix = "门课程"
        text = l.text
        assert text.endswith(suffix)
        courses += int(text[:-len(suffix)])
    return courses

# FUN has an api that returns a count.
@matches("france-universite-numerique-mooc.fr")
async def fun_parser(site, session):
    url = "https://www.fun-mooc.fr/fun/api/courses/?rpp=50&page=1"
    text = await session.text_from_url(url)
    data = json.loads(text)
    return data['count']

@matches("courses.openedu.tw")
async def openedu_tw_parser(site, session):
    url = "https://www.openedu.tw/rest/courses/query"
    text = await session.text_from_url(url)
    data = json.loads(text)
    return len(data)

@matches("openedu.ru")
async def openedu_ru_parser(site, session):
    url = "https://openedu.ru/course/"
    text = await session.text_from_url(url)
    count = element_by_css(text, "span#courses-found")
    assert " кур" in count.text
    return int(count.text.split()[0])

@matches("gacco.org")
async def gacco_parser(site, session):
    url = "http://gacco.org/data/course/gacco_list.json"
    text = await session.text_from_url(url)
    data = json.loads(text)
    count = len(data["opened_courses"])

    url = "http://gacco.org/data/course/gacco_archive.json"
    text = await session.text_from_url(url)
    data = json.loads(text)
    count += len(data["archived_courses"])
    return count

@matches("doroob.sa", "/ar/individuals/elearning/", ".courses-listing-item")
@matches("labster.com", "/simulations/", ".md-simulation-card")
@matches("wasserx.com", "/courses/", "li.course-item")
async def count_elements_parser(site, session, relurl, css):
    url = urllib.parse.urljoin(site.url, relurl)
    text = await session.text_from_url(url)
    elts = elements_by_css(text, css)
    count = len(elts)
    return count

@matches("millionlights.org")
async def millionlights_parser(site, session):
    url = "https://www.millionlights.org/Course/AllCourses"
    text = await session.text_from_url(url)
    # Find the language-faceted results, and add up their parenthesized
    # numbers.
    elts = elements_by_xpath(text, "//a[contains(text(), 'English (')]/ancestor::ul//a")
    count = 0
    for elt in elts:
        result = parse_text("{} ({:d})", elt.text)
        count += result[1]
    return count

@matches("vlabs.ac.in")
async def vlabs_parser(site, session):
    url = "https://vlabs.ac.in/"
    text = await session.text_from_url(url)
    elt = element_by_css(text, "div.features div:first-child div h3")
    result = parse_text("Labs {:d}", elt.text)
    return result[0]

@matches("enlightme.net")
async def enlightme_parser(site, session):
    url = "https://www.enlightme.net/courses/"
    text = await session.text_from_url(url)
    elt = element_by_css(text, ".course-index span")
    result = parse_text("Showing 1-10 of {:d} results", elt.text)
    return result[0]

@matches("skills.med.hku.hk")
async def hku_hk_parser(site, session):
    url = "https://skills.med.hku.hk/mbbs_admin/public/downloadMbbsJsonFile"
    text = await session.text_from_url(url)
    data = json.loads(text)
    count = len(data)
    return count

@matches("skillvideo.nursing.hku.hk")
async def hku_nursing_parser(site, session):
    url = "https://skillvideo.nursing.hku.hk/nurs_admin/public/downloadNursJsonFile"
    text = await session.text_from_url(url)
    data = json.loads(text)
    count = len(data)
    return count

@matches("learning.hku.hk")
async def learning_hku_parser(site, session):
    url = "https://learning.hku.hk/catalog/all-courses/"
    text = await session.text_from_url(url)
    elt = element_by_css(text, "li#course-all span")
    count = int(elt.text)
    return count

@matches("iitbombayx.in")
async def iitbombayx_parser(site, session):
    url = "https://iitbombayx.in/courses"
    text = await session.text_from_url(url)
    elts = elements_by_css(text, "#block-timeline-2 .facet-item__count")
    count = 0
    for elt in elts:
        count += int(elt.text.strip("()"))
    return count

@matches("edraak.org")
async def edraak_org_parser(site, session):
    url = "https://www.edraak.org/en/courses/"
    text = await session.text_from_url(url)
    elts = elements_by_css(text, "aside.all-courses div.course span")
    count = 0
    for elt in elts:
        count += int(elt.text.strip(" ()"))
    return count

@matches("edcast.org")
async def edcast_org_parser(site, session):
    url = "https://www.edcast.org/search"
    text = await session.text_from_url(url)
    h4 = element_by_css(text, ".search-navigation-row h4")
    result = parse_text("All Courses ({:d} matches)", h4.text)
    return result[0]

@matches("cognitiveclass.ai")
@matches("bigdatauniversity.com.cn")
async def cognitiveclass_parser(site, session):
    url = urllib.parse.urljoin(site.url, "/courses")
    count = 0
    while True:
        text = await session.text_from_url(url)
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
    url = urllib.parse.urljoin(site.url, "/course_packages/")
    text = await session.text_from_url(url)
    elt = element_by_css(text, "div#discovery-message")
    result = parse_text("Viewing {:d} courses", elt.text)
    return result[0]

@matches("eso.org.br")
async def prefer_tiles(site, session):
    return await courses_page_full_of_tiles(site, session)

@matches("gotoclass.ir")
async def gotoclass_parser(site, session):
    url = urllib.parse.urljoin(site.url, "/courses/")
    count = 0
    while True:
        text = await session.text_from_url(url)
        elts = elements_by_css(text, "div.course-block")
        count += len(elts)
        next_a = elements_by_css(text, "a.next.page-numbers")
        if not next_a:
            break
        assert len(next_a) == 1
        url = urllib.parse.urljoin(url, next_a[0].get('href'))
    return count

@matches("learn.in.th")
async def learn_in_th_parser(site, session):
    url = urllib.parse.urljoin(site.url, "/main/frontend/ListCourses/listSearch/1")
    text = await session.text_from_url(url)
    data = json.loads(text)
    return data['all_row']


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

async def count_tiles(url, site, session):
    text = await session.text_from_url(url)
    elts = elements_by_css(text, ".courses ul.courses-listing > li")
    count = len(elts)
    if count == 0:
        elts = elements_by_css(text, ".courses-listing-item")
        count = len(elts)
        if count == 0:
            raise Exception("got zero")

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
    return count

@matches_any
async def edx_search_post(site, session):
    real_url = await session.real_url(site.url)
    url0 = urllib.parse.urljoin(real_url, '/courses')
    # Note: the URL says course_discovery, but this is not the Course Discovery
    # app, it routes through to edx-search.
    url = urllib.parse.urljoin(real_url, '/search/course_discovery/')
    text = await session.text_from_url(url, came_from=url0, method='post')
    try:
        data = json.loads(text)
    except Exception:
        raise Exception(f"Couldn't parse result from json: {text[:100]!r}")
    count = data["total"]
    if count == 0:
        raise Exception("got zero")
    try:
        for course in data["results"]:
            site.course_ids[course["_id"]] += 1
    except Exception:
        pass
    return count

@matches_any
async def courses_page_full_of_tiles(site, session):
    url = urllib.parse.urljoin(site.url, "/courses")
    return await count_tiles(url, site, session)

@matches_any
async def home_page_full_of_tiles(site, session):
    return await count_tiles(site.url, site, session)
