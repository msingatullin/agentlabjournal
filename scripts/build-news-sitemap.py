#!/usr/bin/env python3
"""Build a Google News sitemap for recently published journal articles."""
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape
import re

ROOT = Path(__file__).resolve().parent.parent
pages = sorted(list(ROOT.glob("article-*.html")) + list(ROOT.glob("guide-*.html")) + [p for p in (ROOT / "en").glob("*.html") if p.name not in {"index.html", "guides.html", "lead-intake.html"}])
rows = []
for page in pages:
    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', page.read_text())
    title = re.search(r'<title>(.*?)</title>', page.read_text(), re.S)
    if canonical and title:
        rows.append(f"  <url><loc>{escape(canonical.group(1))}</loc><news:news><news:publication><news:name>Agent Lab Journal</news:name><news:language>{'en' if page.parent.name == 'en' else 'ru'}</news:language></news:publication><news:publication_date>{date.today().isoformat()}</news:publication_date><news:title>{escape(re.sub(r'<[^>]+>', '', title.group(1)))}</news:title></news:news></url>")
(ROOT / "news-sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n' + "\n".join(rows) + "\n</urlset>\n")
print(f"News sitemap built: {len(rows)} URLs")
