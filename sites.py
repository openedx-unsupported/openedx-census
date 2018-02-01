"""Parsers for specific sites."""

import json
import urllib.parse

from helpers import elements_by_css, elements_by_xpath
from site_patterns import matches

# XuetangX: add up courses by institution.
@matches(r"www\.xuetangx\.com$")
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
@matches(r"france-universite-numerique-mooc\.fr$")
async def fun_parser(site, session):
    url = "https://www.fun-mooc.fr/fun/api/courses/?rpp=50&page=1"
    text = await session.text_from_url(url)
    data = json.loads(text)
    return data['count']

@matches(r"courses.openedu.tw$")
async def openedu_tw_parser(site, session):
    url = "https://www.openedu.tw/rest/courses/query"
    text = await session.text_from_url(url)
    data = json.loads(text)
    return len(data)

@matches(r"openedu.ru$")
async def openedu_ru_parser(site, session):
    url = "https://openedu.ru/course/"
    text = await session.text_from_url(url)
    count = elements_by_css(text, "span#courses-found")[0]
    assert count.text.endswith(" курс")
    return int(count.text.split()[0])

@matches(r"gacco.org$")
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

@matches(r"doroob.sa$")
async def doroob_parser(site, session):
    url = "https://www.doroob.sa/ar/individuals/elearning/"
    text = await session.text_from_url(url, save=True)
    elts = elements_by_css(text, ".courses-listing-item")
    count = len(elts)
    return count

@matches(r"millionlights.org$")
async def millionlights_parser(site, session):
    # There's a number on the front page, this number is different, but seems
    # more accurate.
    url = "https://www.millionlights.org/Course/GetCourses"
    text = await session.text_from_url(url, method='post')
    data = json.loads(text)
    count = len(data)
    return count

@matches(r"vlabs.ac.in$")
async def vlabs_parser(site, session):
    url = "https://vlabs.ac.in/"
    text = await session.text_from_url(url)
    elt = elements_by_css(text, "div.features div:first-child div h3")[0]
    words = elt.text.strip().split()
    assert words[0] == "Labs"
    count = int(words[1])
    return count

@matches(r"enlightme.net$")
async def enlightme_parser(site, session):
    url = "https://www.enlightme.net/courses/"
    text = await session.text_from_url(url)
    elt = elements_by_css(text, ".course-index span")[0]
    words = elt.text.strip().split()
    assert words[:3] == ["Showing", "1-10", "of"]
    count = int(words[3])
    return count

@matches(r"skills.med.hku.hk$")
async def hku_hk_parser(site, session):
    url = "https://skills.med.hku.hk/mbbs_admin/public/downloadMbbsJsonFile"
    text = await session.text_from_url(url)
    data = json.loads(text)
    count = len(data)
    return count

@matches(r"skillvideo.nursing.hku.hk$")
async def hku_nursing_parser(site, session):
    url = "https://skillvideo.nursing.hku.hk/nurs_admin/public/downloadNursJsonFile"
    text = await session.text_from_url(url)
    data = json.loads(text)
    count = len(data)
    return count

@matches(r"learning.hku.hk$")
async def learning_hku_parser(site, session):
    url = "https://learning.hku.hk/catalog/all-courses/"
    text = await session.text_from_url(url)
    elt = elements_by_css(text, "li#course-all span")[0]
    count = int(elt.text)
    return count

@matches(r"iitbombayx.in$")
async def iitbombayx_parser(site, session):
    url = "https://iitbombayx.in/courses"
    text = await session.text_from_url(url)
    elts = elements_by_css(text, "#block-timeline-2 .facet-item__count")
    count = 0
    for elt in elts:
        count += int(elt.text.strip("()"))
    return count

@matches(r"edraak.org$")
async def edraak_org_parser(site, session):
    url = "https://www.edraak.org/en/courses/"
    text = await session.text_from_url(url)
    elts = elements_by_css(text, "aside.all-courses div.course span")
    count = 0
    for elt in elts:
        count += int(elt.text.strip(" ()"))
    return count

@matches(r"labster.com$")
async def labster_com_parser(site, session):
    url = "https://www.labster.com/simulations/"
    text = await session.text_from_url(url)
    elts = elements_by_css(text, ".md-simulation-card")
    count = len(elts)
    return count


# Generic parsers

async def count_tiles(url, site, session):
    text = await session.text_from_url(url)
    elts = elements_by_css(text, ".courses ul.courses-listing > li")
    count = len(elts)
    if count == 0:
        elts = elements_by_css(text, ".courses-listing-item")
        count = len(elts)
        if count == 0:
            raise Exception("got zero")
    # Try to get the course ids also!
    try:
        for elt in elts:
            course_id = elt.xpath("article/@id")[0]
            site.course_ids[course_id] += 1
    except Exception:
        pass
    return count

@matches(r".")
async def course_discovery_post(site, session):
    real_url = await session.real_url(site.url)
    url0 = urllib.parse.urljoin(real_url, '/courses')
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

@matches(r".")
async def courses_page_full_of_tiles(site, session):
    url = urllib.parse.urljoin(site.url, "/courses")
    return await count_tiles(url, site, session)

@matches(r".")
async def home_page_full_of_tiles(site, session):
    return await count_tiles(site.url, site, session)
