"""Parsers for specific sites."""

import json
import urllib.parse

from helpers import elements_by_css, elements_by_xpath
from site_patterns import matches

# XuetangX: add up courses by institution.
@matches(r"www\.xuetangx\.com$")
async def parser(site, session):
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
async def parser(site, session):
    url = "https://www.fun-mooc.fr/fun/api/courses/?rpp=50&page=1"
    text = await session.text_from_url(url)
    data = json.loads(text)
    return data['count']

@matches(r"courses.openedu.tw$")
async def parser(site, session):
    url = "https://www.openedu.tw/rest/courses/query"
    text = await session.text_from_url(url)
    data = json.loads(text)
    return len(data)

@matches(r"courses.zsmu.edu.ua")
@matches(r"lms.mitx.mit.edu")
@matches(r"memooc\.hu$")
async def courses_page_full_of_tiles(site, session):
    url = urllib.parse.urljoin(site.url, "/courses")
    text = await session.text_from_url(url)
    li = elements_by_css(text, ".courses ul.courses-listing > li")
    return len(li)

@matches(r"openedu.ru$")
async def parser(site, session):
    url = "https://openedu.ru/course/"
    text = await session.text_from_url(url)
    count = elements_by_css(text, "span#courses-found")[0]
    assert count.text.endswith(" курс")
    return int(count.text.split()[0])

@matches(r"puroom.net$")
async def parser(site, session):
    url0 = 'https://lms.puroom.net/courses'
    url = "https://lms.puroom.net/search/course_discovery/"
    text = await session.text_from_url(url, came_from=url0, method='post')
    data = json.loads(text)
    count = data["facets"]["emonitoring_course"]["total"]
    return count

@matches(r"gacco.org$")
async def parser(site, session):
    url = "http://gacco.org/data/course/gacco_list.json"
    text = await session.text_from_url(url)
    data = json.loads(text)
    count = len(data["opened_courses"])

    url = "http://gacco.org/data/course/gacco_archive.json"
    text = await session.text_from_url(url)
    data = json.loads(text)
    count += len(data["archived_courses"])
    return count

# All the rest go here...
@matches(r".")
async def parser(site, session):
    text = await session.text_from_url(site.url)
    return len(text) * 1000
