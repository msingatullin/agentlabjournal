#!/usr/bin/env python3
"""Register an already generated article in all publication indexes."""
from argparse import ArgumentParser
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

parser = ArgumentParser(description="Register and validate an Agent Lab Journal article")
parser.add_argument("--file", required=True, help="HTML filename in the repository root")
parser.add_argument("--summary", required=True, help="Short description for indexes and LLMs")
parser.add_argument("--news", action="store_true", help="Also add the article to Yandex News RSS")
args = parser.parse_args()

relative = Path(args.file)
filename = relative.name
article = ROOT / relative
if article.suffix != ".html" or not article.exists():
    raise SystemExit(f"Article not found in repository root: {filename}")

text = article.read_text()
if "reading-meta" not in text or "canonical" not in text:
    raise SystemExit("Article must contain reading-meta and canonical before registration")

url = f"https://agentlabjournal.online/{filename}"
summary = escape(args.summary)

if relative.parts and relative.parts[0] == "en":
    gate = subprocess.run([sys.executable, str(ROOT / "scripts/check-publication.py")], cwd=ROOT)
    if gate.returncode:
        raise SystemExit("Publication blocked: fix the gate output before committing")
    rss = subprocess.run([sys.executable, str(ROOT / "scripts/build-rss.py")], cwd=ROOT)
    if rss.returncode:
        raise SystemExit("Publication blocked: RSS could not be built")
    print(f"Registered English article: {relative}")
    raise SystemExit(0)

catalog = ROOT / "guides.html"
catalog_text = catalog.read_text()
if filename not in catalog_text:
    marker = "</ol>"
    item = f'<li><a class="text-link" href="{filename}">{escape(article.stem.replace("-", " ").title())}</a></li>'
    if marker not in catalog_text:
        raise SystemExit("Cannot find article list in guides.html")
    catalog.write_text(catalog_text.replace(marker, item + marker, 1))

sitemap = ROOT / "sitemap.xml"
sitemap_text = sitemap.read_text()
if url not in sitemap_text:
    sitemap.write_text(sitemap_text.replace("</urlset>", f"  <url><loc>{url}</loc><changefreq>monthly</changefreq><priority>0.7</priority></url>\n</urlset>", 1))

llms = ROOT / "llms.txt"
llms_text = llms.read_text()
if url not in llms_text:
    line = f"- [{escape(article.stem.replace('-', ' ').title())}]({url}): {summary}.\n"
    llms.write_text(llms_text.replace("## Навигация", line + "\n## Навигация", 1))

if args.news:
    feed = ROOT / "yandex-news.xml"
    feed_text = feed.read_text()
    if url not in feed_text:
        now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
        title = escape(article.stem.replace("-", " ").title())
        item = f"    <item><title>{title}</title><link>{url}</link><guid isPermaLink=\"true\">{url}</guid><pubDate>{now}</pubDate><author>Михаил</author><description>{summary}</description></item>\n"
        feed.write_text(feed_text.replace("  </channel>", item + "  </channel>", 1))

gate = subprocess.run([sys.executable, str(ROOT / "scripts/check-publication.py")], cwd=ROOT)
if gate.returncode:
    raise SystemExit("Publication blocked: fix the gate output before committing")
catalogs = subprocess.run([sys.executable, str(ROOT / "scripts/build-section-catalogs.py")], cwd=ROOT)
if catalogs.returncode:
    raise SystemExit("Publication blocked: section catalogs could not be built")
rss = subprocess.run([sys.executable, str(ROOT / "scripts/build-rss.py")], cwd=ROOT)
if rss.returncode:
    raise SystemExit("Publication blocked: RSS could not be built")
print(f"Registered: {filename}")
