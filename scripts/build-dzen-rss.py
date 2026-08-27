#!/usr/bin/env python3
"""Build a Russian full-text RSS 2.0 feed for Dzen/Yandex ingestion."""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from email.utils import format_datetime
from html.parser import HTMLParser
from pathlib import Path


BASE_URL = "https://agentlabjournal.online/"
YANDEX_NS = "http://news.yandex.ru"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
MEDIA_NS = "http://search.yahoo.com/mrss/"
ATOM_NS = "http://www.w3.org/2005/Atom"
MAX_AGE_DAYS = 8
MAX_FEED_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TAGS = {"p", "h2", "h3", "h4", "ul", "ol", "li", "blockquote", "pre", "code"}
SKIP_TAGS = {"script", "style", "nav", "footer", "form", "button", "svg"}
SKIP_CLASSES = {
    "max-promo-block",
    "journal-cta",
    "service-note",
    "related",
    "related-links",
    "article-footer",
    "social-links",
}

for prefix, uri in (("yandex", YANDEX_NS), ("content", CONTENT_NS), ("media", MEDIA_NS), ("atom", ATOM_NS)):
    ET.register_namespace(prefix, uri)


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.canonical = ""
        self.article_depth = 0
        self.skip_depth = 0
        self.title_depth = 0
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.html_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        classes = set(values.get("class", "").split())
        if tag == "meta":
            key = values.get("property") or values.get("name")
            if key and values.get("content"):
                self.meta[key] = values["content"]
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href", "")

        if tag == "article":
            self.article_depth += 1
        if not self.article_depth:
            return
        if self.skip_depth:
            self.skip_depth += 1
            return
        if tag in SKIP_TAGS or classes.intersection(SKIP_CLASSES):
            self.skip_depth = 1
            return
        if tag == "h1":
            self.title_depth += 1
            return
        if tag in ALLOWED_CONTENT_TAGS:
            self.html_parts.append(f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        if not self.article_depth:
            return
        if self.skip_depth:
            self.skip_depth -= 1
            return
        if tag == "h1" and self.title_depth:
            self.title_depth -= 1
            return
        if tag in ALLOWED_CONTENT_TAGS:
            self.html_parts.append(f"</{tag}>")
            if tag in {"p", "h2", "h3", "h4", "li", "blockquote", "pre"}:
                self.text_parts.append("\n")
        if tag == "article":
            self.article_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.article_depth or self.skip_depth:
            return
        normalized = re.sub(r"\s+", " ", data)
        if not normalized.strip():
            return
        if self.title_depth:
            self.title_parts.append(normalized.strip())
            return
        self.text_parts.append(normalized)
        self.html_parts.append(html.escape(normalized))

    @property
    def title(self) -> str:
        return " ".join(self.title_parts).strip()

    @property
    def full_text(self) -> str:
        return re.sub(r"[ \t]+", " ", "".join(self.text_parts)).strip()

    @property
    def encoded_html(self) -> str:
        return "".join(self.html_parts).strip()


def parse_datetime(value: str) -> dt.datetime:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return dt.datetime.combine(dt.date.fromisoformat(value), dt.time(), dt.timezone(dt.timedelta(hours=3)))
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"publication date lacks timezone: {value}")
    return parsed


def json_ld_date(source: str) -> str | None:
    for payload in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', source, re.I | re.S):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            if isinstance(node, dict) and node.get("datePublished"):
                return str(node["datePublished"])
    return None


def git_publication_date(root: Path, page: Path) -> dt.datetime | None:
    result = subprocess.run(
        ["git", "log", "--diff-filter=A", "--follow", "--format=%aI", "--", page.name],
        cwd=root,
        text=True,
        capture_output=True,
    )
    values = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return parse_datetime(values[-1]) if result.returncode == 0 and values else None


def publication_date(root: Path, page: Path, source: str, parser: ArticleParser) -> dt.datetime | None:
    value = parser.meta.get("article:published_time") or json_ld_date(source)
    return parse_datetime(value) if value else git_publication_date(root, page)


def add_text(parent: ET.Element, tag: str, value: str) -> ET.Element:
    node = ET.SubElement(parent, tag)
    node.text = value
    return node


def build_item(root: Path, page: Path, now: dt.datetime) -> tuple[dt.datetime, ET.Element] | None:
    source = page.read_text(encoding="utf-8")
    parser = ArticleParser()
    parser.feed(source)
    if not parser.title or not parser.canonical.startswith(BASE_URL) or not parser.full_text:
        return None
    published = publication_date(root, page, source, parser)
    if published is None or published > now or now - published > dt.timedelta(days=MAX_AGE_DAYS):
        return None

    item = ET.Element("item")
    add_text(item, "title", parser.title)
    add_text(item, "link", parser.canonical)
    guid = add_text(item, "guid", parser.canonical)
    guid.set("isPermaLink", "true")
    add_text(item, "pubDate", format_datetime(published))
    add_text(item, "author", "Михаил")
    description = parser.meta.get("description") or parser.full_text[:300]
    add_text(item, "description", description)
    section = parser.meta.get("article:section")
    if section:
        add_text(item, "category", section)
    add_text(item, f"{{{YANDEX_NS}}}genre", "article")
    add_text(item, f"{{{YANDEX_NS}}}full-text", parser.full_text)
    add_text(item, f"{{{CONTENT_NS}}}encoded", parser.encoded_html)
    image = parser.meta.get("og:image")
    if image:
        thumbnail = ET.SubElement(item, f"{{{MEDIA_NS}}}thumbnail")
        thumbnail.set("url", image)
    return published, item


def build_feed(root: Path, output: Path, now: dt.datetime) -> int:
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    add_text(channel, "title", "Agent Lab Journal")
    add_text(channel, "link", BASE_URL)
    add_text(channel, "description", "Практические материалы об AI-агентах, автоматизации и проверяемых системах.")
    add_text(channel, "language", "ru")
    add_text(channel, "lastBuildDate", format_datetime(now))
    atom = ET.SubElement(channel, f"{{{ATOM_NS}}}link")
    atom.set("href", f"{BASE_URL}dzen-rss.xml")
    atom.set("rel", "self")
    atom.set("type", "application/rss+xml")

    candidates = []
    for page in sorted(root.glob("*.html")):
        built = build_item(root, page, now)
        if built:
            candidates.append(built)
    candidates.sort(key=lambda row: row[0], reverse=True)
    for _, item in candidates:
        channel.append(item)

    ET.indent(rss, space="  ")
    payload = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    if len(payload) > MAX_FEED_BYTES:
        raise SystemExit(f"DZEN_RSS: feed exceeds 10 MiB ({len(payload)} bytes)")
    output.write_bytes(payload + b"\n")
    return len(candidates)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--now", help="ISO-8601 clock override for deterministic tests")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve() if args.output else root / "dzen-rss.xml"
    now = parse_datetime(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
    count = build_feed(root, output, now)
    print(f"DZEN_RSS: built {count} items at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
