import textwrap


class HtmlOutlineWriter:
    """Write an HTML file with nested collapsable sections."""

    HEAD = textwrap.dedent(r"""
        <!DOCTYPE html>
        <html>
        <head>
        <title>[[TITLE]]</title>
        <meta charset="utf-8" />
        <style>
        .toggle-box {
            display: none;
        }

        .toggle-box + label {
            cursor: pointer;
            display: block;
            line-height: 21px;
            margin-bottom: 5px;
        }

        .toggle-box + label + div {
            display: none;
            margin-bottom: 10px;
        }

        .toggle-box:checked + label + div {
            display: block;
            padding-left: 2em;
        }

        .toggle-box + label:before {
            color: #888;
            content: "\25B8";
            display: block;
            float: left;
            height: 20px;
            line-height: 20px;
            margin-right: 5px;
            text-align: center;
            width: 20px;
        }

        .toggle-box:checked + label:before {
            content: "\25BE";
        }

        [[CSS]]

        </style>
        </head>
        <body>
    """)

    SECTION_START = textwrap.dedent("""\
        <div class="{klass}">
        <input class="toggle-box {klass}" id="sect_{id:05d}" type="checkbox">
        <label for="sect_{id:05d}">{html}</label>
        <div>
    """)

    SECTION_END = "</div></div>"

    def __init__(self, fout, css="", title=""):
        self.fout = fout
        self.section_id = 0
        head = self.HEAD
        head = head.replace("[[CSS]]", textwrap.dedent(css))
        head = head.replace("[[TITLE]]", title)
        self.fout.write(head)

    def start_section(self, html, klass=None):
        self.fout.write(self.SECTION_START.format(
            id=self.section_id, html=html, klass=klass or "",
        ))
        self.section_id += 1

    def end_section(self):
        self.fout.write(self.SECTION_END)

    def write(self, html):
        self.fout.write(html)
