#!/usr/bin/env python3
"""Build non-publishing distribution drafts from an existing article."""
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent

def meta(html, name):
    m = re.search(r'<meta[^>]+(?:name|property)=["\']' + re.escape(name) + r'["\'][^>]+content=["\']([^"\']*)', html, re.I)
    return m.group(1).strip() if m else ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--out", default="out/distribution")
    args = ap.parse_args()
    path = ROOT / args.file
    if not path.exists(): raise SystemExit(f"article not found: {args.file}")
    html = path.read_text(encoding="utf-8")
    canonical = meta(html, "og:url") or meta(html, "canonical")
    if not canonical:
        m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', html, re.I)
        canonical = m.group(1) if m else ""
    if not canonical.startswith("https://"):
        raise SystemExit("DISTRIBUTION_GATE: BLOCKED (canonical missing)")
    title = meta(html, "og:title") or (re.search(r'<title>(.*?)</title>', html, re.I|re.S) or ["", ""])[1].strip()
    description = meta(html, "description") or meta(html, "og:description")
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    tracked = urlsplit(canonical)
    query = urlencode({"utm_source":"agentlabjournal", "utm_medium":"distribution", "utm_campaign":"editorial", "utm_content":path.stem})
    tracked_url = urlunsplit((tracked.scheme, tracked.netloc, tracked.path, query, ""))
    out = ROOT / args.out / f"{path.stem}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status":"draft", "generated_at":datetime.now(timezone.utc).isoformat(),
        "source_article":str(path.relative_to(ROOT)), "canonical":canonical,
        "tracked_url":tracked_url, "title":title, "description":description,
        "telegram":{"text":f"{title}\n\n{description}\n\nЧитать: {tracked_url}"},
        "linkedin_x":{"text":f"{title}\n\n{description}\n\n{tracked_url}"},
        "short_video":{"hook":title, "outline":["Проблема", "Проверка", "Результат"], "source_url":canonical},
        "manual_review_required":True,
        "fact_check":{"source_article_only":True, "raw_text_length":len(text)}
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"DISTRIBUTION_PACK: OK {out.relative_to(ROOT)}")

if __name__ == "__main__": main()
