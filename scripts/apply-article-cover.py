#!/usr/bin/env python3
"""Apply one approved cover to one RU or EN article."""
from argparse import ArgumentParser
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://agentlabjournal.online/"
parser = ArgumentParser()
parser.add_argument("--file", required=True)
args = parser.parse_args()
relative = Path(args.file)
page = ROOT / relative
if not page.exists() or page.suffix != ".html":
    raise SystemExit(f"ARTICLE_COVER: article missing: {relative}")

covers = json.loads((ROOT / "homepage-covers.json").read_text(encoding="utf-8"))
row = covers.get(page.stem)
if not row or not all(row.get(key) for key in ("path", "social_path", "alt", "evidence", "type")):
    raise SystemExit(f"ARTICLE_COVER: approved cover metadata missing: {page.stem}")
cover = ROOT / row["path"]
if not cover.exists():
    raise SystemExit(f"ARTICLE_COVER: cover file missing: {row['path']}")
social_cover = ROOT / row["social_path"]
if not social_cover.exists():
    raise SystemExit(f"ARTICLE_COVER: social cover file missing: {row['social_path']}")

prefix = "../" if relative.parts and relative.parts[0] == "en" else ""
local_src = prefix + row["path"]
url = BASE + row["social_path"]
text = page.read_text(encoding="utf-8")


def meta(text: str, key: str, value: str, *, prop: bool = False) -> str:
    attr = "property" if prop else "name"
    pattern = rf'<meta[^>]+{attr}=["\']{re.escape(key)}["\'][^>]*>'
    tag = f'<meta {attr}="{key}" content="{escape(value)}">'
    if re.search(pattern, text, re.I):
        return re.sub(pattern, tag, text, count=1, flags=re.I)
    return text.replace("</head>", f"  {tag}\n</head>", 1)


text = meta(text, "og:image", url, prop=True)
text = meta(text, "og:image:alt", row["alt"], prop=True)
text = meta(text, "twitter:image", url)
text = re.sub(r'("image"\s*:\s*)(?:\[[^\]]*\]|"[^"]*")', rf'\1["{url}"]', text, count=1, flags=re.S)
marker = f'data-editorial-cover="{page.stem}"'
if marker not in text:
    figure = (
        f'\n        <figure class="article-cover" {marker}>'
        f'<img src="{escape(local_src)}" alt="{escape(row["alt"])}" width="1280" height="720" fetchpriority="high">'
        f'<figcaption>{escape(row["evidence"])}</figcaption></figure>'
    )
    text, count = re.subn(r"(</h1>)", rf"\1{figure}", text, count=1, flags=re.I)
    if count != 1:
        raise SystemExit(f"ARTICLE_COVER: h1 missing: {relative}")
page.write_text(text, encoding="utf-8")
print(f"ARTICLE_COVER: OK {relative} <- {row['path']}")
