#!/usr/bin/env python3
"""Add the metadata required by search and discovery surfaces to articles."""
from datetime import date
from html import escape
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent.parent
TODAY = date.today().isoformat()
IMAGE = "https://agentlabjournal.online/podcast-cover.png"

def articles():
    pages = list(ROOT.glob("article-*.html")) + list(ROOT.glob("guide-*.html"))
    pages += [p for p in (ROOT / "en").glob("*.html") if p.name.startswith(("article-", "guide-"))]
    return sorted(pages)

def meta(name, content, *, prop=False):
    key = "property" if prop else "name"
    return f'<meta {key}="{escape(name)}" content="{escape(content)}">'

def upgrade(page):
    text = page.read_text()
    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', text)
    title = re.search(r'<title>(.*?)</title>', text, re.S)
    description = re.search(r'<meta name="description" content="([^"]*)"', text)
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S)
    if not (canonical and title and description and h1):
        raise SystemExit(f"metadata gate: incomplete head in {page}")
    url = canonical.group(1)
    title_text = re.sub(r"<[^>]+>", "", title.group(1)).strip()
    description_text = description.group(1)
    language = "en" if page.parent.name == "en" else "ru"
    additions = "\n".join([
        meta("author", "Agent Lab Journal"),
        meta("robots", "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"),
        meta("googlebot", "index,follow,max-image-preview:large"),
        meta("date", TODAY),
        meta("og:type", "article", prop=True),
        meta("og:title", title_text, prop=True),
        meta("og:description", description_text, prop=True),
        meta("og:url", url, prop=True),
        meta("og:image", IMAGE, prop=True),
        meta("og:image:width", "1200", prop=True),
        meta("og:image:height", "630", prop=True),
        meta("og:site_name", "Agent Lab Journal", prop=True),
        meta("og:locale", "en_US" if language == "en" else "ru_RU", prop=True),
        meta("twitter:card", "summary_large_image"),
        meta("twitter:title", title_text),
        meta("twitter:description", description_text),
        meta("twitter:image", IMAGE),
        f'<link rel="alternate" type="application/rss+xml" title="Agent Lab Journal ({language})" href="https://agentlabjournal.online/{"rss-en.xml" if language == "en" else "rss.xml"}">',
    ])
    text = re.sub(r'(<title>.*?</title>)', r'\1\n' + additions, text, count=1, flags=re.S)
    ld = {
        "@context": "https://schema.org", "@type": "Article", "headline": re.sub(r"<[^>]+>", "", h1.group(1)).strip(),
        "description": description_text, "image": [IMAGE], "dateModified": TODAY,
        "author": {"@type": "Organization", "name": "Agent Lab Journal", "url": "https://agentlabjournal.online/"},
        "publisher": {"@type": "Organization", "name": "Agent Lab Journal", "url": "https://agentlabjournal.online/", "logo": {"@type": "ImageObject", "url": IMAGE}},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url}, "inLanguage": language,
    }
    replacement = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False, separators=(",", ":")) + '</script>'
    text, count = re.subn(r'<script type="application/ld\+json">.*?</script>', replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"metadata gate: JSON-LD missing in {page}")
    page.write_text(text)

for page in articles():
    upgrade(page)
print(f"SEO metadata upgraded: {len(articles())} articles")
