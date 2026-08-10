#!/usr/bin/env python3
"""Verify podcast news against ready NotebookLM primary sources."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from podcast_contract import read_json, write_json

NOTEBOOKLM = "/root/.venvs/notebooklm/bin/notebooklm"
DEFAULT_NOTEBOOK = "fb0f2035-2378-47c1-9add-e7f27b223d56"
PRIMARY_DOMAINS = {
    "news.microsoft.com", "blogs.nvidia.com", "github.blog", "nist.gov", "www.nist.gov",
    "digital-strategy.ec.europa.eu", "ec.europa.eu", "duma.gov.ru", "aws.amazon.com",
    "nvd.nist.gov",
    "arxiv.org", "www.frontiersin.org",
}


def source_contains_date(content: str, value: dt.date) -> bool:
    month = value.strftime("%B")
    patterns = (
        rf"\b{re.escape(month)}\s+{value.day},\s+{value.year}\b",
        rf"\b{value.day}\s+{re.escape(month)}\s+{value.year}\b",
        rf"\b{value.month:02d}/{value.day:02d}/{value.year}\b",
        rf"\b{value.isoformat()}\b",
    )
    return any(re.search(pattern, content, re.I) for pattern in patterns)


def command_json(command: list[str]) -> dict:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-3000:])
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--notebook", default=DEFAULT_NOTEBOOK)
    args = parser.parse_args()
    package = read_json(args.input)
    target = dt.date.fromisoformat(package["date"])
    window_days = int(package.get("news_window_days", 2))
    allowed_dates = {target - dt.timedelta(days=offset) for offset in range(window_days)}
    sources_payload = command_json([NOTEBOOKLM, "source", "list", "--notebook", args.notebook, "--json"])
    sources = {item["id"]: item for item in sources_payload.get("sources", [])}
    evidence = []
    for item in package.get("news", []):
        source = sources.get(item.get("source_id"))
        if not source or source.get("status") != "ready":
            raise ValueError(f"Source is missing or not ready: {item.get('source_id')}")
        if source.get("url") != item.get("source_url"):
            raise ValueError(f"Source URL mismatch: {item['title']}")
        if urlparse(item["source_url"]).hostname not in PRIMARY_DOMAINS:
            raise ValueError(f"Non-primary source rejected: {item['source_url']}")
        if dt.date.fromisoformat(item["date"]) not in allowed_dates:
            raise ValueError(f"News is outside previous-24h date window: {item['title']}")
        fulltext = command_json([NOTEBOOKLM, "source", "fulltext", item["source_id"], "--notebook", args.notebook, "--json"])
        raw_content = fulltext.get("content") or ""
        content = raw_content.casefold()
        content_compact = re.sub(r"\s+", " ", content).strip()
        item_date = dt.date.fromisoformat(item["date"])
        date_evidence = "source_text"
        if not source_contains_date(raw_content, item_date):
            raise ValueError(f"Claimed date is absent from primary source text: {item['title']} ({item_date})")
        missing = [
            term for term in item["evidence_terms"]
            if re.sub(r"\s+", " ", term.casefold()).strip() not in content_compact
        ]
        if missing:
            raise ValueError(f"Evidence terms missing for {item['title']}: {missing}")
        item["verification_status"] = "verified"
        evidence.append({"source_id": item["source_id"], "url": item["source_url"], "terms": item["evidence_terms"], "date_evidence": date_evidence})
    package["fact_gate"] = {
        "status": "passed", "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(), "evidence": evidence,
    }
    write_json(args.output, package)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
