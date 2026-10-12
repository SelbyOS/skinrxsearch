# SkinRxsearch — a living look
Biweekly skincare, ingredient, product, tool and hair/scalp research scan. Entries live in `entries/*.json`; `python3 build.py` merges them into `site/index.html`, which Netlify serves. Not medical advice.

## Hiding and removing entries
- **Hide (per device):** the Hide button in a dossier removes an entry from your feed, Compare picker and Runs list on that device only. A Hidden filter appears to bring it back. Included in Export / Import.
- **Archive (everyone, permanently):** set `"archived": true` in the entry's JSON and rebuild. It disappears from the site and from the Markdown batches. The file stays in git history.
- **Run cover:** `meta.json` → `runs[].cover` = `{url, alt, credit, creditUrl, pos}`. If the image fails to load, a gradient shows instead.
- **Notes:** several per entry, stored in the browser. Select text in a dossier and tap Add selection to capture it with its section label.
