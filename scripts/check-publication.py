#!/usr/bin/env python3
"""Publication gate for Agent Lab Journal."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
guides = sorted(list(ROOT.glob("guide-*.html")) + list(ROOT.glob("article-*.html")))
english_guides = sorted(p for p in (ROOT / "en").glob("*.html") if p.name not in {"index.html", "lead-intake.html"})
required = {
    "reading-meta": "reading metadata",
    "glossary.html": "glossary link",
    "canonical": "canonical URL",
    "meta name=\"description\"": "description",
    '"@type":"Article"': "Article JSON-LD",
}
errors = []
titles = {}

for page in guides:
    text = page.read_text()
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S | re.I)
    if title_match:
        title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip().casefold()
        if title in titles:
            errors.append(f"{page.name}: duplicate title with {titles[title]}")
        else:
            titles[title] = page.name
    for marker, label in required.items():
        if marker not in text:
            errors.append(f"{page.name}: missing {label}")

for page in english_guides:
    text = page.read_text()
    for markers, label in ((("reading-meta",), "reading metadata"), (("canonical",), "canonical URL"), (("meta name=\"description\"",), "description"), (("\"@type\":\"Article\"", "\"@type\": \"Article\""), "Article JSON-LD"), (("lang=\"en\"",), "English lang attribute")):
        if not any(marker in text for marker in markers):
            errors.append(f"en/{page.name}: missing {label}")

catalog = (ROOT / "guides.html").read_text()
sitemap = (ROOT / "sitemap.xml").read_text()
llms = (ROOT / "llms.txt").read_text()

for page in guides:
    url = page.name
    if url not in catalog:
        errors.append(f"{url}: missing from guides.html")
    if url not in sitemap:
        errors.append(f"{url}: missing from sitemap.xml")
    if url not in llms:
        errors.append(f"{url}: missing from llms.txt")
    if not any(url in (ROOT / f"section-{section}.html").read_text() for section in ("news", "practice", "companies", "tools", "experiments", "errors", "security", "money", "opinions")):
        errors.append(f"{url}: missing from section catalog")

for page in english_guides:
    url = f"en/{page.name}"
    if url not in sitemap:
        errors.append(f"{url}: missing from sitemap.xml")
    if f"https://agentlabjournal.online/{url}" not in llms:
        errors.append(f"{url}: missing from llms.txt")

for term in ("glossary.html", "guides.html", "sitemap.xml"):
    if term not in llms and term != "sitemap.xml":
        errors.append(f"llms.txt: missing navigation link to {term}")
if "sections.html" not in llms:
    errors.append("llms.txt: missing navigation link to sections.html")

if errors:
    print("PUBLICATION_GATE: BLOCKED")
    print("\n".join(f"- {item}" for item in errors))
    sys.exit(1)

print(f"PUBLICATION_GATE: OK ({len(guides)} RU + {len(english_guides)} EN articles checked)")
