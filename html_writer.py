import textwrap

class HtmlOutlineWriter:
    """Write an HTML file with nested collapsable sections."""

    HEAD = textwrap.dedent(r"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8" />
        <style>
        html {
            font-family: sans-serif;
        }
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

        .error, .skipped {
            margin-left: 2em;
        }

        .count {
            font-weight: bold;
        }

        .test {
            margin-left: 2em;
        }

        .stdout {
            margin-left: 2em;
            font-family: Consolas, monospace;
        }
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

    def __init__(self, fout):
        self.fout = fout
        self.section_id = 0
        self.fout.write(self.HEAD)

    def start_section(self, html, klass=None):
        self.fout.write(self.SECTION_START.format(
            id=self.section_id, html=html, klass=klass or "",
        ))
        self.section_id += 1

    def end_section(self):
        self.fout.write(self.SECTION_END)

    def write(self, html):
        self.fout.write(html)
