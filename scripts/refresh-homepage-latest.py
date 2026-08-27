#!/usr/bin/env python3
"""Refresh only the homepage issue date and latest-articles rail."""
from datetime import date, datetime
from html import escape
import json
from pathlib import Path
import re
import runpy


ROOT = Path(__file__).resolve().parent.parent
MONTHS = ("", "января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")


def parsed_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def date_ru(value) -> str:
    current = parsed_date(value)
    return f"{current.day} {MONTHS[current.month]} {current.year}"


def refresh(path: Path, items: list[dict], *, issue_date) -> None:
    text = path.read_text(encoding="utf-8")
    current = parsed_date(issue_date)
    issue_pattern = r'(<div class="issue-line"><time datetime=")[^"]+("[^>]*>)[^<]+(</time>)'
    text, issue_count = re.subn(
        issue_pattern,
        rf'\g<1>{current.isoformat()}\g<2>{date_ru(current)}\g<3>',
        text,
        count=1,
    )
    latest_html = "\n".join(
        f'          <li><a href="{escape(item["path"])}"><time datetime="{parsed_date(item["created"]).isoformat()}">{date_ru(item["created"])}</time><span>{escape(item["title"])}</span></a></li>'
        for item in items
    )
    rail_pattern = r'(<aside class="latest-rail"[^>]*>.*?<ol>).*?(</ol>)'
    text, rail_count = re.subn(
        rail_pattern,
        lambda match: match.group(1) + latest_html + match.group(2),
        text,
        count=1,
        flags=re.S,
    )
    if issue_count != 1 or rail_count != 1:
        raise SystemExit("HOMEPAGE_LATEST: expected issue line and latest rail exactly once")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    builder = runpy.run_path(str(ROOT / "scripts" / "build-homepage.py"))
    item_map = builder["articles"]()
    config = json.loads((ROOT / "homepage-editorial.json").read_text(encoding="utf-8"))
    excluded = {config["lead"], *config["editors_choice"], *config["deep_reads"]}
    latest = sorted(
        (row for row in item_map.values() if row["slug"] not in excluded),
        key=lambda row: row["created"],
        reverse=True,
    )[:6]
    if not latest:
        raise SystemExit("HOMEPAGE_LATEST: no eligible articles")
    refresh(ROOT / "index.html", latest, issue_date=latest[0]["created"])
    print(f"HOMEPAGE_LATEST: updated {len(latest)} articles through {latest[0]['created'].date().isoformat()}")


if __name__ == "__main__":
    main()
