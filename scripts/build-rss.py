#!/usr/bin/env python3
"""Build the general RSS feed used by external publishing platforms."""
import html
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
items = []
for page in sorted(ROOT.glob("*.html")):
    if not (page.name.startswith("guide-") or page.name.startswith("article-") or page.name.endswith("-case.html")):
        continue
    text = page.read_text()
    title = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S | re.I)
    description = re.search(r'<meta name="description" content="([^"]*)"', text, re.I)
    if not title:
        continue
    clean_title = re.sub(r"<[^>]+>", "", title.group(1)).strip()
    url = f"https://agentlabjournal.online/{page.name}"
    items.append(f"    <item><title>{html.escape(clean_title)}</title><link>{url}</link><guid isPermaLink=\"true\">{url}</guid><pubDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate><description>{html.escape(description.group(1) if description else clean_title)}</description></item>")

feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Agent Lab Journal</title>
  <link>https://agentlabjournal.online/</link>
  <description>Practical notes on reliable AI agents, automation and safety.</description>
  <language>en</language>
  <lastBuildDate>""" + datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000') + """</lastBuildDate>
""" + "\n".join(items) + "\n</channel></rss>\n"
(ROOT / "rss.xml").write_text(feed)
print(f"RSS: built {len(items)} items")
