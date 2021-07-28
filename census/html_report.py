import collections
from xml.sax.saxutils import escape

from census.helpers import domain_from_url, is_chaff_domain, is_known
from census.html_writer import HtmlOutlineWriter
from census.report_helpers import get_known_domains, hash_sites_together, sort_sites

CSS = """\
    html {
        font-family: sans-serif;
    }

    pre {
        font-family: Consolas, monospace;
    }

    .url {
        font-weight: bold;
    }
    .hash {
        color: #aaa;
        font-size: 75%;
    }
    .strategy {
        font-style: italic;
    }
    .tag {
        display: inline-block;
        background: #cccccc;
        font-size: 75%;
        margin: 0 .1em .1em;
        padding: 0 .3em;
        border-radius: 3px;
    }
    .tag.slow {
        background: #d5efa7;
    }
    .tag.none {
        background: #f09393;
    }
    .tag.drastic {
        background: #ebe377;
    }
    .tag.new {
        background: yellow;
        border: 1px solid #ddd;
        margin: -1px 0;
    }
    .tag.ssl {
        background: #ff8080;
    }
    .tag.bad {
        background: red;
        border: 2px solid black;
        color: white;
        padding: 0 .5em;
    }
    .tag.version {
        background: lime;
        border-radius: 1em;
        padding: 0 .5em;
    }
    .info {
        margin: 0 0 0 1.5em;
    }
"""


def html_report(out_file, sites, old, new, all_courses=None, all_orgs=None, only_new=False):
    sites = sort_sites(sites)
    known_domains = get_known_domains()

    writer = HtmlOutlineWriter(out_file, css=CSS, title=f"Census: {len(sites)} sites")
    header = f"{len(sites)} sites: {old}"
    if new != old:
        header += f" &rarr; {new}"
    writer.start_section(header)
    for site in sites:
        write_site(site, writer, known_domains)
    writer.end_section()

    if all_courses:
        total_course_ids = sum(len(sites) for sites in all_courses.values())
        writer.start_section(f"<p>Course IDs: {total_course_ids}</p>")
        all_courses_items = sorted(all_courses.items())
        all_courses_items = sorted(all_courses_items, key=lambda item: len(item[1]), reverse=True)
        for course_id, cid_sites in all_courses_items:
            writer.start_section(f"{course_id}: {len(cid_sites)}")
            for site in sorted(cid_sites, key=lambda s: s.url):
                writer.write(f"<p><a class='url' href='{site.url}'>{site.url}</a></p>")
            writer.end_section()
        writer.end_section()

    if all_orgs:
        shared_orgs = [(org, sites) for org, sites in all_orgs.items() if len(sites) > 1]
        writer.start_section(f"<p>Shared orgs: {len(shared_orgs)}</p>")
        for org, org_sites in sorted(shared_orgs):
            writer.start_section(f"{org}: {len(org_sites)}")
            for site in sorted(org_sites, key=lambda s: s.url):
                writer.write(f"<p><a class='url' href='{site.url}'>{site.url}</a></p>")
            writer.end_section()
        writer.end_section()

    hashed_sites = hash_sites_together(sites, known_domains, only_new)

    versions = collections.defaultdict(list)
    tags = collections.defaultdict(list)
    for hashed_site in hashed_sites:
        versions[hashed_site.version or "none"].append(hashed_site)
        for tag in hashed_site.tags():
            tags[tag].append(hashed_site)

    writer.start_section(f"<p>Versions</p>")
    for version in sorted(versions.keys()):
        hsites = versions[version]
        writer.start_section(f"<p>{version}: {len(hsites)}</p>")
        for hashed_site in hsites:
            write_hashed_site(hashed_site, writer, known_domains)
        writer.end_section()
    writer.end_section()

    writer.start_section(f"<p>Tags</p>")
    for tag in sorted(tags.keys()):
        hsites = tags[tag]
        writer.start_section(f"<p>{tag}: {len(hsites)}</p>")
        for hashed_site in hsites:
            write_hashed_site(hashed_site, writer, known_domains)
        writer.end_section()
    writer.end_section()

    writer.start_section(f"<p>Hashed: {len(hashed_sites)}</p>")
    for hashed_site in hashed_sites:
        write_hashed_site(hashed_site, writer, known_domains)
    writer.end_section()


def write_hashed_site(hashed_site, writer, known_domains):
    tags = Tags()
    if hashed_site.all_chaff():
        tags.add("Chaff")
    if hashed_site.is_new:
        tags.add("New")
    if hashed_site.all_ssl_err():
        tags.add("SSL")
    url = hashed_site.best_url()
    ncourses = hashed_site.current_courses()
    nsites = len(hashed_site.sites)
    writer.start_section(
        f"<a class='url' href='{url}'>{url}</a>&nbsp; "
        f"<b>{ncourses}</b> {pluralize(ncourses, 'course')}, "
        f"{nsites} {pluralize(nsites, 'site')} {tags.html()}"
    )
    for site in hashed_site.sites:
        write_site(site, writer, known_domains)
    info = hashed_site.other_info()
    if info:
        writer.write(f"<p class='info'><b>Info:</b> {'; '.join(sorted(info))}</p>")
    writer.end_section()

def write_site(site, writer, known_domains):
    old, new = site.latest_courses, site.current_courses
    tags = Tags()

    new_text = ""
    if new is None:
        tags.add("None")
    else:
        if new != old:
            new_text = f"<b> &rarr; {new}</b>"
        if old != 0 and new != 0 and abs(new - old) > 10 and not (0.5 >= old/new >= 1.5):
            tags.add("Drastic")
    if is_chaff_domain(domain_from_url(site.url)):
        tags.add("Chaff")
    elif not is_known(site, known_domains):
        tags.add("New")
    # Times are not right now that we limit requests, not sites.
    #if site.time > 5:
    #    tags.add(f"{site.time:.1f}s", "slow")
    for tag, style in sorted(site.styled_tags()):
        tags.add(tag, style)

    writer.start_section(f"<a class='url' href='{site.url}'>{site.url}</a>: {old}{new_text} {tags.html()}")
    for attempt in site.tried:
        strategy = attempt.strategy
        tb = attempt.error
        if tb is not None:
            lines = tb.splitlines()
            if len(lines) > 1:
                line = tb.splitlines()[-1][:100]
                writer.start_section(f"<span class='strategy'>{strategy}:</span> {escape(line)}")
                writer.write("""<pre class="stdout">""")
                writer.write(escape(tb))
                writer.write("""</pre>""")
                writer.end_section()
            else:
                writer.write(f"<p>{strategy}: {lines[0]}")
        else:
            writer.write(f"<p>{strategy}: counted {attempt.courses} courses</p>")
    writer.end_section()


class Tags:
    def __init__(self):
        self.tags = []

    def add(self, text, tag_name=None):
        self.tags.append(f"<span class='tag {tag_name or text.lower()}'>{text}</span>")

    def html(self):
        return ''.join(self.tags)


def pluralize(n, s, ss=None):
    """Make a word plural (in English)"""
    if ss is None:
        ss = s + "s"
    if n == 1:
        return s
    else:
        return ss
