import collections
from xml.sax.saxutils import escape

from html_writer import HtmlOutlineWriter

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
"""


def html_report(out_file, sites, old, new, all_courses=None, all_orgs=None):
    writer = HtmlOutlineWriter(out_file, css=CSS, title=f"Census: {len(sites)} sites")
    header = f"{len(sites)} sites: {old}"
    if new != old:
        header += f" &rarr; {new}"
    writer.start_section(header)
    for site in sites:
        write_site(site, writer)
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
            for site in org_sites:
                writer.write(f"<p><a class='url' href='{site.url}'>{site.url}</a></p>")
            writer.end_section()
        writer.end_section()

    fps = collections.defaultdict(list)
    for site in sites:
        fps[site.fingerprint].append(site)
    writer.start_section(f"<p>Hashes</p>")
    fps = sorted(fps.items(), key=lambda kv: kv[1][0].current_courses, reverse=True)
    for fp, fp_sites in fps:
        writer.start_section(f"{fp}: <b>{fp_sites[0].current_courses}</b> courses, {len(fp_sites)} sites")
        for site in fp_sites:
            writer.write(f"<p><a class='url' href='{site.url}'>{site.url}</a></p>")
        writer.end_section()
    writer.end_section()


def write_site(site, writer):
    def tag_it(text, tag_name=None):
        tags.append(f"<span class='tag {tag_name or text.lower()}'>{text}</span>")

    old, new = site.latest_courses, site.current_courses
    tags = []

    new_text = ""
    if new is None:
        tag_it("None")
    else:
        if new != old:
            new_text = f"<b> &rarr; {new}</b>"
        if abs(new - old) > 10 and not (0.5 >= old/new >= 1.5):
            tag_it("Drastic")
    if site.is_gone_now:
        tag_it("Gone")
    elif site.is_gone:
        tag_it("Back")
    # Times are not right now that we limit requests, not sites.
    #if site.time > 5:
    #    tag_it(f"{site.time:.1f}s", "slow")
    writer.start_section(f"<a class='url' href='{site.url}'>{site.url}</a>: {old}{new_text} {''.join(tags)}")
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
