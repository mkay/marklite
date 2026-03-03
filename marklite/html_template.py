from pygments.formatters import HtmlFormatter


def _pygments_css(dark=False):
    style = "monokai" if dark else "default"
    return HtmlFormatter(style=style).get_style_defs(".highlight")


def wrap_html(body_html, font_family="Sans", font_size=16, dark=False):
    pygments_css = _pygments_css(dark)

    if dark:
        bg = "#242424"
        fg = "#e0e0e0"
        link = "#6ea8fe"
        code_bg = "#363636"
        border = "#555"
        heading_border = "#444"
        blockquote_border = "#555"
        blockquote_fg = "#aaa"
        table_th_bg = "#363636"
        table_border = "#444"
        hr_color = "#444"
    else:
        bg = "#ffffff"
        fg = "#1a1a1a"
        link = "#0366d6"
        code_bg = "#f5f5f5"
        border = "#ddd"
        heading_border = "#ddd"
        blockquote_border = "#ddd"
        blockquote_fg = "#666"
        table_th_bg = "#f5f5f5"
        table_border = "#ddd"
        hr_color = "#ddd"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    font-family: {font_family}, sans-serif;
    font-size: {font_size}px;
    line-height: 1.6;
    color: {fg};
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    background: {bg};
}}
h1, h2, h3, h4, h5, h6 {{
    margin-top: 1.2em;
    margin-bottom: 0.4em;
    line-height: 1.3;
}}
h1 {{ font-size: 1.8em; border-bottom: 1px solid {heading_border}; padding-bottom: 0.2em; }}
h2 {{ font-size: 1.5em; border-bottom: 1px solid {heading_border}; padding-bottom: 0.2em; }}
h3 {{ font-size: 1.25em; }}
a {{ color: {link}; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
code {{
    font-family: monospace;
    background: {code_bg};
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.9em;
}}
pre {{
    position: relative;
    background: {code_bg};
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    line-height: 1.4;
}}
.copy-btn {{
    position: absolute;
    top: 6px;
    right: 6px;
    background: none;
    border: 1px solid {border};
    border-radius: 4px;
    cursor: pointer;
    padding: 4px;
    opacity: 0;
    transition: opacity 0.15s;
    display: flex;
    align-items: center;
    justify-content: center;
    color: {fg};
}}
pre:hover .copy-btn {{ opacity: 0.7; }}
.copy-btn:hover {{ opacity: 1 !important; background: {code_bg}; }}
.copy-btn:active {{ transform: scale(0.95); }}
.copy-btn.copied {{ opacity: 1; }}
pre code {{
    background: none;
    padding: 0;
}}
blockquote {{
    margin: 0.8em 0;
    padding: 0.4em 1em;
    border-left: 4px solid {blockquote_border};
    color: {blockquote_fg};
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}}
table th, table td {{
    border: 1px solid {table_border};
    padding: 8px 12px;
    text-align: left;
}}
table th {{
    background: {table_th_bg};
    font-weight: 600;
}}
img {{
    max-width: 100%;
    height: auto;
}}
hr {{
    border: none;
    border-top: 1px solid {hr_color};
    margin: 1.5em 0;
}}
ul, ol {{
    padding-left: 1.5em;
}}
li {{ margin: 0.3em 0; }}
{pygments_css}
/* WebKit find-in-page highlight overrides */
::highlight(search) {{ background-color: #ffdd00 !important; color: #000 !important; }}
::highlight(current) {{ background-color: #ff6a00 !important; color: #fff !important; }}
</style>
</head>
<body>
{body_html}
<script>
document.addEventListener("DOMContentLoaded", function() {{
    var svgIcon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
    document.querySelectorAll("pre").forEach(function(pre) {{
        var btn = document.createElement("button");
        btn.className = "copy-btn";
        btn.title = "Copy code";
        btn.innerHTML = svgIcon;
        btn.addEventListener("click", function() {{
            var code = pre.querySelector("code");
            var raw = (code || pre).textContent;
            var text = raw.split("\\n").filter(function(line) {{
                var t = line.trim();
                return t !== "" && !t.startsWith("#");
            }}).join("\\n");
            window.webkit.messageHandlers.copyCode.postMessage(text);
            btn.innerHTML = "Copied!";
            btn.classList.add("copied");
            setTimeout(function() {{
                btn.innerHTML = svgIcon;
                btn.classList.remove("copied");
            }}, 1500);
        }});
        pre.appendChild(btn);
    }});
}});
</script>
</body>
</html>"""
