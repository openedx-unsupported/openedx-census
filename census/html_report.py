import collections
from xml.sax.saxutils import escape

from census.helpers import domain_from_url, is_chaff_domain, is_known
from census.html_writer import HtmlOutlineWriter
from census.sites import HashedSite

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
"""


def html_report(out_file, sites, old, new, all_courses=None, all_orgs=None, known_domains=None, only_new=False):

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

    hashed_sites = collections.defaultdict(HashedSite)
    for site in sites:
        hashed_site = hashed_sites[site.fingerprint]
        hashed_site.fingerprint = site.fingerprint
        hashed_site.sites.append(site)

    writer.start_section(f"<p>Hashed: {len(hashed_sites)}</p>")
    hashed_sites = sorted(hashed_sites.items(), key=lambda kv: kv[1].current_courses() or 0, reverse=True)
    for fp, hashed_site in hashed_sites:
        tags = Tags()
        is_new = False
        if hashed_site.all_chaff():
            tags.add("Chaff")
        else:
            is_new = not hashed_site.any_known(known_domains)
        if only_new and not is_new:
            continue
        if is_new:
            tags.add("New")
        if all(site.ssl_err for site in hashed_site.sites):
            tags.add("SSL")
        url = hashed_site.best_url()
        ncourses = hashed_site.current_courses()
        nsites = len(hashed_site.sites)
        writer.start_section(
            f"<a class='url' href='{url}'>{url}</a>&nbsp; "
            #f"<span class='hash'>{fp[:10]}</span>&nbsp; "
            f"<b>{ncourses}</b> {pluralize(ncourses, 'course')}, "
            f"{nsites} {pluralize(nsites, 'site')} {tags.html()}"
        )
        for site in hashed_site.sites:
            write_site(site, writer, known_domains)
        writer.end_section()
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
    if site.is_gone_now:
        tags.add("Gone")
    elif site.is_gone:
        tags.add("Back")
    if is_chaff_domain(domain_from_url(site.url)):
        tags.add("Chaff")
    elif not is_known(site, known_domains):
        tags.add("New")
    if site.ssl_err:
        tags.add("SSL")
    if site.custom_parser_err:
        tags.add("Custom parser error", "bad")
    if site.version:
        tags.add(site.version, "version")
    # Times are not right now that we limit requests, not sites.
    #if site.time > 5:
    #    tags.add(f"{site.time:.1f}s", "slow")
    writer.start_section(f"<a class='url' href='{site.url}'>{site.url}</a>: {old}{new_text} {tags.html()}")
    for strategy, tb in site.tried:
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
            writer.write(f"<p>{strategy}: worked</p>")
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
