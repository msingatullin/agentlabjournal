#!/usr/bin/env python3
"""Build a bounded podcast candidate without NotebookLM.

The fallback uses the existing source collector, accepts only allow-listed
primary domains, verifies the publication date in the fetched page, and keeps
verbatim evidence excerpts for the downstream fact gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from podcast_contract import HOSTS, INTRO_EXACT, OUTRO_EXACT, expected_rubric, write_json

PROJECT = Path("/root/agentlabjournal")
PRIMARY_DOMAINS = {
    "news.microsoft.com", "blogs.nvidia.com", "github.blog", "nist.gov", "www.nist.gov",
    "digital-strategy.ec.europa.eu", "ec.europa.eu", "duma.gov.ru", "aws.amazon.com",
    "arxiv.org", "www.frontiersin.org",
}


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "AgentLabJournalFallback/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read(2_000_000).decode(response.headers.get_content_charset() or "utf-8", "replace")
    raw = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", raw, flags=re.I | re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def evidenced_date(text: str, target: dt.date) -> dt.date | None:
    for offset in range(7):
        value = target - dt.timedelta(days=offset)
        month = value.strftime("%B")
        patterns = (
            rf"\b{value.isoformat()}(?:T|\b)",
            rf"\b{re.escape(month)}\s+{value.day},\s+{value.year}\b",
            rf"\b{value.day}\s+{re.escape(month)}\s+{value.year}\b",
        )
        if any(re.search(pattern, text, re.I) for pattern in patterns):
            return value
    return None


def excerpts(text: str, title: str) -> list[str]:
    chunks = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text)]
    usable = [part for part in chunks if 80 <= len(part) <= 420 and title.casefold() not in part.casefold()]
    return [" ".join(part.split()[:24]) for part in usable[:3]]


def build(target: dt.date) -> dict:
    candidates = json.loads((PROJECT / "article-source-candidates.json").read_text(encoding="utf-8"))
    selected = []
    for candidate in candidates:
        url = candidate.get("url", "")
        if candidate.get("status") == "rejected" or urlparse(url).hostname not in PRIMARY_DOMAINS:
            continue
        try:
            content = fetch_text(url)
        except Exception:
            continue
        published = evidenced_date(content, target)
        terms = excerpts(content, candidate.get("title", ""))
        if not published or len(terms) < 3:
            continue
        title = re.sub(r"\s+", " ", candidate.get("title", "")).strip()
        description = re.sub(r"<[^>]+>", " ", candidate.get("description", ""))
        description = re.sub(r"\s+", " ", html.unescape(description)).strip()
        claim = description[:700].rstrip(" .") + "." if description else f"Официальный источник опубликовал материал «{title}»."
        selected.append({
            "title": title,
            "date": published.isoformat(),
            "source_id": "direct:" + hashlib.sha256(url.encode()).hexdigest()[:20],
            "source_url": url,
            "claim": claim,
            "why_it_matters": "Материал даёт проверяемый первичный контекст для практической работы с AI-системами.",
            "evidence_terms": terms,
            "qa_terms": ["первичный источник", "проверка фактов", "практическое применение"],
            "source_provider": "direct",
        })
        if len(selected) == 3:
            break
    if len(selected) < 2:
        raise RuntimeError("DIRECT_RESEARCH_GATE: fewer than two dated primary sources")
    oldest = min(dt.date.fromisoformat(item["date"]) for item in selected)
    window = min(7, (target - oldest).days + 1)
    label = "Новости за последние 24 часа" if window <= 2 else ("Новости за последние 72 часа" if window <= 3 else "Новости за последние 7 дней")
    titles = "; ".join(item["title"] for item in selected)
    return {
        "date": target.isoformat(), "language": "ru", "rubric": expected_rubric(target.isoformat()),
        "hosts": HOSTS, "intro_exact": INTRO_EXACT, "news": selected,
        "news_window_days": 2 if window <= 2 else (3 if window <= 3 else 7),
        "news_window_label": label,
        "daily_topic": "Практические изменения в AI-разработке по материалам первичных источников",
        "listener_takeaway": f"В резервный выпуск вошли проверяемые материалы: {titles}.",
        "outro_exact": OUTRO_EXACT, "research_provider": "direct_fallback",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or PROJECT / "podcasts/packages" / f"{args.date}-ru.candidate.json"
    write_json(output, build(dt.date.fromisoformat(args.date)))
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
