#!/usr/bin/env python3
"""Build SkinRxsearch.

entries/*.json + meta.json + src/index.html (+ src/icons.json, compiled Tailwind)
  -> site/index.html   full static document (what Netlify serves)
  -> out/page.html     fragment for a claude.ai Artifact preview

Tailwind is compiled at build time (npx tailwindcss@3.4.17) and inlined. If npx is
unavailable the last compiled copy in src/compiled.css is used, so a build never fails
for network reasons. Run: python3 build.py
"""
import glob, json, os, subprocess, sys, tempfile

root = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(root, *a)

entries = []
for p in sorted(glob.glob(P("entries", "*.json"))):
    with open(p, encoding="utf-8") as f:
        entries.append(json.load(f))
entries.sort(key=lambda e: (e.get("run", ""), e.get("id", "")), reverse=True)
meta = json.load(open(P("meta.json"), encoding="utf-8")) if os.path.exists(P("meta.json")) else {}
icons = json.load(open(P("src", "icons.json"), encoding="utf-8"))

def js(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")

# --- Tailwind ---
src = open(P("src", "index.html"), encoding="utf-8").read()
css = None
tmp = tempfile.mktemp(suffix=".css")
try:
    r = subprocess.run(["npx", "--yes", "tailwindcss@3.4.17", "-c", P("tailwind.config.js"),
                        "-i", P("src", "input.css"), "-o", tmp, "--minify"],
                       capture_output=True, text=True, timeout=240, cwd=root)
    if r.returncode == 0 and os.path.exists(tmp):
        css = open(tmp, encoding="utf-8").read()
        open(P("src", "compiled.css"), "w", encoding="utf-8").write(css)
    else:
        print("tailwind failed, using cached css:", r.stderr[-300:], file=sys.stderr)
except Exception as ex:
    print("tailwind unavailable, using cached css:", ex, file=sys.stderr)
if css is None:
    css = open(P("src", "compiled.css"), encoding="utf-8").read()

data = "window.SRS_META=%s;window.SRS_ENTRIES=%s;window.SRS_ICONS=%s;" % (js(meta), js(entries), js(icons))
assert "/*__DATA__*/" in src and "/*__CSS__*/" in src
fragment = src.replace("/*__CSS__*/", css.replace("</", "<\\/")).replace("/*__DATA__*/", data)

os.makedirs(P("out"), exist_ok=True)
open(P("out", "page.html"), "w", encoding="utf-8").write(fragment)

doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       '<meta name="robots" content="noindex">\n<meta name="color-scheme" content="light dark">\n</head>\n<body>\n'
       + fragment + '\n</body>\n</html>\n')
os.makedirs(P("site"), exist_ok=True)
open(P("site", "index.html"), "w", encoding="utf-8").write(doc)
print("built %d entries -> site/index.html (%d KB), out/page.html" % (len(entries), len(doc) // 1024))
