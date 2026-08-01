#!/usr/bin/env python3
"""Apply approved cover metadata and figures to the curated RU articles."""
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://agentlabjournal.online/"
covers = json.loads((ROOT / "homepage-covers.json").read_text(encoding="utf-8"))


def meta(text: str, key: str, value: str, *, prop: bool = False) -> str:
    attr = "property" if prop else "name"
    pattern = rf'<meta[^>]+{attr}=["\']{re.escape(key)}["\'][^>]*>'
    tag = f'<meta {attr}="{key}" content="{escape(value)}">'
    if re.search(pattern, text, re.I):
        return re.sub(pattern, tag, text, count=1, flags=re.I)
    return text.replace("</head>", f"  {tag}\n</head>", 1)


for slug, row in covers.items():
    page = ROOT / f"{slug}.html"
    if not page.exists():
        if row.get("publication_status") == "planned":
            print(f"COVER_APPLY: planned article not present yet: {page.name}")
            continue
        raise SystemExit(f"COVER_APPLY: article missing: {page.name}")
    cover = ROOT / row["path"]
    if not cover.exists():
        raise SystemExit(f"COVER_APPLY: cover missing: {row['path']}")
    social_cover = ROOT / row["social_path"]
    if not social_cover.exists():
        raise SystemExit(f"COVER_APPLY: social cover missing: {row['social_path']}")
    text = page.read_text(encoding="utf-8")
    url = BASE + row["social_path"]
    text = meta(text, "og:image", url, prop=True)
    text = meta(text, "og:image:alt", row["alt"], prop=True)
    text = meta(text, "twitter:image", url)
    text = re.sub(r'("image"\s*:\s*)(?:\[[^\]]*\]|"[^"]*")', rf'\1["{url}"]', text, count=1, flags=re.S)
    marker = f'data-editorial-cover="{slug}"'
    if marker not in text:
        figure = (
            f'\n        <figure class="article-cover" {marker}>'
            f'<img src="{escape(row["path"])}" alt="{escape(row["alt"])}" width="1280" height="720" fetchpriority="high">'
            f'<figcaption>{escape(row["evidence"])}</figcaption></figure>'
        )
        text, count = re.subn(r"(</h1>)", rf"\1{figure}", text, count=1, flags=re.I)
        if count != 1:
            raise SystemExit(f"COVER_APPLY: h1 missing: {page.name}")
    page.write_text(text, encoding="utf-8")
    print(f"COVER_APPLY: {page.name} <- {row['path']}")
