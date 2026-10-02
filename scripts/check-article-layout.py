#!/usr/bin/env python3
"""Fail closed when an article lacks the canonical page skeleton.

Required: site header (site-header or masthead), a bounded reading container
(main.article, article.reading or another .reading element), a page-level
footer outside the article, and for Russian articles a service-note.
"""
from argparse import ArgumentParser
from html.parser import HTMLParser
from pathlib import Path


class LayoutParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = ""
        self.article_depth = 0
        self.has_site_header = False
        self.has_reading_container = False
        self.has_site_footer = False
        self.has_service_note = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "html":
            self.lang = (attributes.get("lang") or "").lower()
        if tag == "header" and {"site-header", "masthead"} & set(classes):
            self.has_site_header = True
        if (tag == "main" and "article" in classes) or "reading" in classes:
            self.has_reading_container = True
        if tag == "footer" and ("site-footer" in classes or self.article_depth == 0):
            self.has_site_footer = True
        if "service-note" in classes:
            self.has_service_note = True
        if tag == "article":
            self.article_depth += 1

    def handle_endtag(self, tag):
        if tag == "article" and self.article_depth:
            self.article_depth -= 1


parser = ArgumentParser()
parser.add_argument("--file", required=True)
args = parser.parse_args()

page = Path(args.file)
document = LayoutParser()
document.feed(page.read_text(encoding="utf-8"))
english = document.lang.startswith("en") or (not document.lang and "en" in page.parts)

missing = []
if not document.has_site_header:
    missing.append("site header (header.site-header or header.masthead)")
if not document.has_reading_container:
    missing.append("bounded reading container (main.article or .reading)")
if not document.has_site_footer:
    missing.append("page footer (footer.site-footer or footer outside <article>)")
if not english and not document.has_service_note:
    missing.append("service-note")

if missing:
    print(f"ARTICLE_LAYOUT_GATE: BLOCKED ({page.name}: missing {'; '.join(missing)})")
    raise SystemExit(1)

print(f"ARTICLE_LAYOUT_GATE: OK ({page.name}, {'en' if english else 'ru'})")
