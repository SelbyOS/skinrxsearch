#!/usr/bin/env python3
"""Build SkinRxsearch.

entries/*.json + meta.json + src/index.html (+ src/icons.json, compiled Tailwind)
  -> site/index.html   full static document (what Netlify serves)
  -> out/page.html     fragment for a claude.ai Artifact preview

Tailwind is compiled at build time (npx tailwindcss@3.4.17) and inlined. If npx is
unavailable the last compiled copy in src/compiled.css is used, so a build never fails
for network reasons. Run: python3 build.py
"""
import glob, json, os, re, subprocess, sys, tempfile

root = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(root, *a)

entries = []
for p in sorted(glob.glob(P("entries", "*.json"))):
    with open(p, encoding="utf-8") as f:
        entries.append(json.load(f))
entries = [e for e in entries if not e.get("archived")]  # archived: true removes an entry from site and Markdown
entries.sort(key=lambda e: (e.get("run", ""), e.get("id", "")), reverse=True)
meta = json.load(open(P("meta.json"), encoding="utf-8")) if os.path.exists(P("meta.json")) else {}
icons = json.load(open(P("src", "icons.json"), encoding="utf-8"))

def js(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")


# ---------- Markdown ----------
def short_cite(c):
    c = c or ""
    m = re.search(r"(19|20)\d\d", c)
    first = c.split(",")[0].split(".")[0].strip()
    return ((first + " et al. ") if first else "") + (m.group(0) if m else "")

def sources_of(e):
    out, seen = [], set()
    def add(label, url):
        if url and url.startswith("http") and url not in seen:
            seen.add(url); out.append((label, url))
    d = e.get("dossier") or {}
    for s in d.get("studies", []):
        sc = short_cite(s.get("cite")) or "Study"
        add(sc + " (DOI)", s.get("doi")); add(sc + " (PubMed)", s.get("pubmed"))
        add(sc + " (full text)", s.get("pmc")); add(sc + " (source)", s.get("url"))
    for p in (d.get("products") or {}).get("items", []):
        add(p.get("name", "Product") + " (listing)", p.get("link"))
    for l in e.get("links", []):
        add(l.get("label", "Source"), l.get("url"))
    return out

def entry_md(e):
    d = e.get("dossier") or {}
    L = []
    w = L.append
    w("# [ENTRY] %s" % e.get("title", ""))
    w("- **Verdict:** %s | **Lane:** %s | **Run:** %s" % (e.get("verdict"), e.get("lane"), e.get("run")))
    w("- **Evidence:** %s of %s. %s" % (e.get("evidenceScore", "?"), e.get("evidenceScale", 5), e.get("evidenceTier", "")))
    w("- **Human trial:** %s | **Skin-tone data:** %s" % ("yes" if e.get("humanTrial") else "none found", e.get("toneData", "unknown")))
    w("- **Tags:** " + ", ".join(e.get("tags", [])))
    w("\n## EXECUTIVE SUMMARY\n" + (e.get("headline") or ""))
    for x in e.get("summaryPoints", []): w("- " + x)
    w("\n## FIT AND REPLACEMENT LOGIC (my judgment, not a measurement)")
    if e.get("fit"): w("- **Fit for you:** %s %s" % (e.get("fitRating", ""), e["fit"]))
    for a in e.get("fitAxes", []): w("- **%s:** %s. %s" % (a["axis"], a["rating"], a.get("why", "")))
    if e.get("displaces"): w("- **What it displaces:** " + e["displaces"])
    if d:
        if d.get("whatItIs"): w("\n## WHAT IT IS\n" + d["whatItIs"])
        if d.get("structure"): w("- **Structure:** %s, SMILES %s (flat 2D, stereochemistry omitted). Record: %s" % (d["structure"].get("formula"), d["structure"].get("smiles"), d["structure"].get("link")))
        m = d.get("mechanism") or {}
        if m:
            w("\n## MECHANISM")
            if m.get("flow"): w(" -> ".join("%s [%s]" % (n["label"], n.get("basis", "")) for n in m["flow"]))
            for i, st in enumerate(m.get("steps", []), 1): w("%d. %s" % (i, st))
            if m.get("inferenceFlag"): w("- **Inference, not observation:** " + m["inferenceFlag"])
        w("\n## STUDIES")
        for s in d.get("studies", []):
            w("### " + s.get("cite", ""))
            w("- **Read depth:** " + str(s.get("readDepth", "not stated")))
            for k, lab in (("design", "Design"), ("who", "Who was included"), ("effectSize", "Effect size"), ("placebo", "Placebo comparison"),
                           ("material", "Material outcome"), ("adverse", "Adverse events"), ("conflict", "Funding and conflicts"), ("limits", "Limits")):
                if s.get(k): w("- **%s:** %s" % (lab, s[k]))
            for r in s.get("results", []): w("  - " + r)
        if d.get("claimsCheck"):
            w("\n## CLAIMS CHECK")
            for c in d["claimsCheck"]: w("- %s | source: %s | %s" % (c["claim"], c["source"], c["status"]))
        pr = d.get("products") or {}
        if pr:
            w("\n## PRODUCTS AND FORMULATIONS")
            if pr.get("rankNote"): w(pr["rankNote"])
            for p in pr.get("items", []): w("- **%s** (%s): %s. %s [%s]" % (p.get("name"), p.get("maker", ""), p.get("price", ""), p.get("note", ""), p.get("verified", "")))
        if d.get("howToUse"):
            w("\n## HOW TO ADAPT IT")
            for x in d["howToUse"]: w("- " + x)
        if d.get("expect"):
            w("\n## WHAT TO EXPECT, AND WHEN")
            for x in d["expect"]: w("- **%s:** %s" % (x["when"], x["what"]))
        if d.get("contraindications"): w("\n## SAFETY\n- **Contraindications and unknowns:** " + d["contraindications"])
        if d.get("sideBenefits"): w("- **Side benefits:** " + d["sideBenefits"])
        if d.get("transfer"): w("\n## DOES IT TRANSFER?\n" + d["transfer"])
        if d.get("wouldChangeVerdict"):
            w("\n## WHAT WOULD CHANGE THE VERDICT")
            for x in d["wouldChangeVerdict"]: w("- " + x)
    if e.get("cost"):
        w("\n## COST AND MARKETS")
        for c in e["cost"]: w("- **%s** (%s): %s" % (c["label"], c["kind"], c["value"]))
        if e.get("buzzCheck"): w("- **Buzz check:** " + e["buzzCheck"])
    w("\n## SOURCES")
    srcs = sources_of(e)
    for lab, url in srcs: w("- [%s](%s)" % (lab, url))
    if not srcs: w("- none linked")
    if d.get("confidence"):
        w("\n## CONFIDENCE AND GAPS")
        for x in d["confidence"]: w("- " + x)
        if d.get("searchedOn"): w("- Searched on " + d["searchedOn"])
    return "\n".join(L) + "\n"

for e in entries:
    e["md"] = entry_md(e)

bdir = P("site", "batches")
os.makedirs(bdir, exist_ok=True)
for f in glob.glob(os.path.join(bdir, "*.md")): os.remove(f)
runs = sorted({e.get("run", "") for e in entries}, reverse=True)
for r in runs:
    note = next((x.get("note", "") for x in meta.get("runs", []) if x.get("date") == r), "")
    body = "# SkinRxsearch batch %s\n\n%s\n\nPrices marked EST are guesses. Read depth is stated per study.\n\n---\n\n" % (r, note)
    body += "\n---\n\n".join(e["md"] for e in entries if e.get("run") == r)
    open(os.path.join(bdir, "batch-%s.md" % r), "w", encoding="utf-8").write(body)
open(os.path.join(bdir, "all-entries.md"), "w", encoding="utf-8").write(
    "# SkinRxsearch: all entries\n\n---\n\n" + "\n---\n\n".join(e["md"] for e in entries))

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
