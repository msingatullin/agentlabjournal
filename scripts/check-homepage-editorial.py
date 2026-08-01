#!/usr/bin/env python3
"""Fail publication when the editorial homepage is stale or structurally incomplete."""
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []
config = json.loads((ROOT / "homepage-editorial.json").read_text(encoding="utf-8"))
covers = json.loads((ROOT / "homepage-covers.json").read_text(encoding="utf-8"))
page = (ROOT / "index.html").read_text(encoding="utf-8")
css = (ROOT / "homepage.css").read_text(encoding="utf-8")

configured = [config["lead"], *config["editors_choice"], *config["deep_reads"]]
if len(configured) != len(set(configured)):
    errors.append("editorial selection contains duplicate slugs")
if len(config["editors_choice"]) != 3 or len(config["deep_reads"]) != 2:
    errors.append("editorial selection must contain 3 choices and 2 deep reads")

for slug in configured:
    if not (ROOT / f"{slug}.html").exists():
        errors.append(f"article missing: {slug}.html")
    row = covers.get(slug)
    if not row:
        errors.append(f"cover metadata missing: {slug}")
        continue
    if not row.get("path") or not row.get("social_path") or not row.get("alt") or not row.get("evidence") or not row.get("type"):
        errors.append(f"cover provenance incomplete: {slug}")
    elif not (ROOT / row["path"]).exists():
        errors.append(f"cover file missing: {row['path']}")
    elif not (ROOT / row["social_path"]).exists():
        errors.append(f"social cover file missing: {row['social_path']}")
    if f'{slug}.html' not in page:
        errors.append(f"configured article absent from homepage: {slug}")

updated = datetime.fromisoformat(config["updated_at"])
if datetime.now(updated.tzinfo) - updated > timedelta(days=7):
    errors.append("editorial selection is older than 7 days")

required_html = (
    'class="masthead"', 'class="mobile-menu"', 'class="front-page"',
    'class="lead-story"', 'class="latest-rail"', 'class="choice-grid"',
    'class="deep-list"', 'class="section-index"',
)
for marker in required_html:
    if marker not in page:
        errors.append(f"homepage marker missing: {marker}")
if page.count('class="story-card"') != 3:
    errors.append("homepage must render exactly 3 editor-choice cards")
if page.count('class="deep-story"') != 2:
    errors.append("homepage must render exactly 2 deep-read cards")
if page.count('loading="lazy"') < 5:
    errors.append("below-fold covers must use lazy loading")
if page.count('fetchpriority="high"') != 1:
    errors.append("homepage must have exactly one high-priority cover")

for marker in (
    "overflow-x: clip", "minmax(0, 1fr)", "overflow-wrap: anywhere",
    "@media (min-width: 40rem)", "@media (min-width: 60rem)",
    "@media (pointer: coarse)", "@media (prefers-reduced-motion: reduce)",
):
    if marker not in css:
        errors.append(f"responsive CSS marker missing: {marker}")

links = re.findall(r'href="([^"]+)"', page)
for href in links:
    if href.startswith(("http://", "https://", "#", "mailto:")):
        continue
    target = href.split("#", 1)[0].split("?", 1)[0]
    if not target:
        continue
    path = ROOT / target
    if target.endswith("/"):
        path = path / "index.html"
    if not path.exists():
        errors.append(f"broken homepage link: {href}")

if errors:
    print("HOMEPAGE_EDITORIAL_GATE: BLOCKED")
    print("\n".join(f"- {error}" for error in errors))
    sys.exit(1)
print(f"HOMEPAGE_EDITORIAL_GATE: OK (1 lead, 6 latest, 3 choice, 2 deep, {len(configured)} covers)")
