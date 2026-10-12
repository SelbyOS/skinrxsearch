#!/usr/bin/env python3
"""Merge entries/*.json + meta.json into the page.

Outputs (run from anywhere):
  out/page.html      fragment for a claude.ai Artifact (no doctype/html/head/body)
  site/index.html    full static document for Netlify drop/deploy

Each scheduled run adds entries/<date>-<slug>.json files (or edits status
fields on old ones), then runs this script, then publishes.
"""
import glob, json, os, sys

root = os.path.dirname(os.path.abspath(__file__))
entries = []
for p in sorted(glob.glob(os.path.join(root, "entries", "*.json"))):
    with open(p, encoding="utf-8") as f:
        entries.append(json.load(f))
entries.sort(key=lambda e: (e.get("run", ""), e.get("id", "")), reverse=True)

meta_path = os.path.join(root, "meta.json")
meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}

def js(obj):
    # keep the inline script safe: no literal </script> or <!-- in the data
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")

data = "window.SRS_META=%s;window.SRS_ENTRIES=%s;" % (js(meta), js(entries))
src = open(os.path.join(root, "index.html"), encoding="utf-8").read()
assert "/*__DATA__*/" in src, "placeholder missing in index.html"
fragment = src.replace("/*__DATA__*/", data)

os.makedirs(os.path.join(root, "out"), exist_ok=True)
open(os.path.join(root, "out", "page.html"), "w", encoding="utf-8").write(fragment)

# Full document wrapper for static hosting. The <title> inside the fragment
# stays; browsers hoist it into the head.
doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       '<meta name="robots" content="noindex">\n</head>\n<body>\n' + fragment + '\n</body>\n</html>\n')
os.makedirs(os.path.join(root, "site"), exist_ok=True)
open(os.path.join(root, "site", "index.html"), "w", encoding="utf-8").write(doc)
# remove the older split data file if present
old = os.path.join(root, "site", "data.js")
if os.path.exists(old):
    os.remove(old)
print("built %d entries -> out/page.html, site/index.html" % len(entries))
sys.exit(0)
