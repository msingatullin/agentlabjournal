#!/usr/bin/env python3
"""Fail closed when a newly published article lacks the readable-width container."""
from argparse import ArgumentParser
from html.parser import HTMLParser
from pathlib import Path


class MainParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.has_bounded_article_container = False

    def handle_starttag(self, tag, attrs):
        if tag != "main":
            return
        classes = dict(attrs).get("class", "").split()
        if "article" in classes:
            self.has_bounded_article_container = True


parser = ArgumentParser()
parser.add_argument("--file", required=True)
args = parser.parse_args()

page = Path(args.file)
markup = page.read_text(encoding="utf-8")
document = MainParser()
document.feed(markup)

if not document.has_bounded_article_container:
    print(f"ARTICLE_LAYOUT_GATE: BLOCKED ({page.name}: missing bounded article container)")
    raise SystemExit(1)

print(f"ARTICLE_LAYOUT_GATE: OK ({page.name})")
