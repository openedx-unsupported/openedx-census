import collections
from xml.sax.saxutils import escape

from census.helpers import domain_from_url, is_chaff_domain
from census.html_writer import HtmlOutlineWriter

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
            for site in cid_sites:
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

    fps = collections.defaultdict(list)
    for site in sites:
        fps[site.fingerprint].append(site)
    writer.start_section(f"<p>Hashed</p>")
    fps = sorted(fps.items(), key=lambda kv: kv[1][0].current_courses, reverse=True)
    for fp, fp_sites in fps:
        if fp is None:
            continue
        tags = Tags()
        is_new = False
        is_chaff = all(is_chaff_domain(domain_from_url(site.url)) for site in fp_sites)
        if is_chaff:
            tags.add("Chaff")
        else:
            any_known = any(is_known(site, known_domains) for site in fp_sites)
            is_new = not any_known
        if only_new and not is_new:
            continue
        if is_new:
            tags.add("New")
        non_chaff = [site for site in fp_sites if not is_chaff_domain(site.url)]
        if non_chaff:
            url = non_chaff[0].url
        else:
            url = fp_sites[0].url
        writer.start_section(
            f"<a class='url' href='{url}'>{url}</a> "
            f"<span class='hash'>{fp[:10]}</span>&nbsp; "
            f"<b>{fp_sites[0].current_courses}</b> courses, "
            f"{len(fp_sites)} sites {tags.html()}"
        )
        for site in fp_sites:
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


def is_known(site, known_domains):
    domain = domain_from_url(site.url)
    for prefix in ['', 'www.']:
        dom = domain
        if domain.startswith(prefix):
            dom = domain[len(prefix):]
        if dom in known_domains:
            return True
    return False

class Tags:
    def __init__(self):
        self.tags = []

    def add(self, text, tag_name=None):
        self.tags.append(f"<span class='tag {tag_name or text.lower()}'>{text}</span>")

    def html(self):
        return ''.join(self.tags)
