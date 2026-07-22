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
    summary = html.escape(description.group(1) if description else clean_title)
    items.append(f"    <item><title>{html.escape(clean_title)}</title><link>{url}</link><guid isPermaLink=\"true\">{url}</guid><pubDate>{datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate><author>journal@agentlabjournal.online (Agent Lab Journal)</author><description>{summary}</description><content:encoded><![CDATA[<p>{summary}</p><p><a href=\"{url}\">Read the original article</a></p>]]></content:encoded></item>")

feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:atom="http://www.w3.org/2005/Atom"><channel>
  <title>Agent Lab Journal</title>
  <link>https://agentlabjournal.online/</link>
  <atom:link href="https://agentlabjournal.online/rss.xml" rel="self" type="application/rss+xml" />
  <description>Practical notes on reliable AI agents, automation and safety.</description>
  <language>en</language>
  <lastBuildDate>""" + datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000') + """</lastBuildDate>
""" + "\n".join(items) + "\n</channel></rss>\n"
(ROOT / "rss.xml").write_text(feed)
english_item = '''    <item><title>Agent Lab Journal: practical AI agent engineering</title><link>https://agentlabjournal.online/en/</link><guid isPermaLink="true">https://agentlabjournal.online/en/</guid><pubDate>''' + datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000') + '''</pubDate><author>journal@agentlabjournal.online (Agent Lab Journal)</author><description>English entry point for practical notes on reliable AI agents, automation, memory and safety.</description><content:encoded><![CDATA[<p>English entry point for Agent Lab Journal.</p><p><a href="https://agentlabjournal.online/en/">Read the journal</a></p>]]></content:encoded></item>'''
english_feed = feed.split("</channel>", 1)[0].replace("rss.xml", "rss-en.xml") + english_item + "\n</channel></rss>\n"
(ROOT / "rss-en.xml").write_text(english_feed)
print(f"RSS: built {len(items)} items")
