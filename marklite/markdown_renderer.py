import re

import markdown


class MarkdownRenderer:
    def __init__(self):
        self._extensions = [
            "fenced_code",
            "codehilite",
            "tables",
            "toc",
            "smarty",
            "attr_list",
            "md_in_html",
        ]
        self._extension_configs = {
            "codehilite": {
                "css_class": "highlight",
                "guess_lang": True,
            },
        }

    def render(self, text):
        md = markdown.Markdown(
            extensions=self._extensions,
            extension_configs=self._extension_configs,
        )
        html = md.convert(text)
        # Convert task-list items: <li>[ ] ... and <li>[x] ...
        html = re.sub(
            r"<li>\[ \]",
            '<li class="task-item"><input type="checkbox"> ',
            html,
        )
        html = re.sub(
            r"<li>\[[xX]\]",
            '<li class="task-item"><input type="checkbox" checked> ',
            html,
        )
        return html
