#!/usr/bin/env python3
"""Research agent: build a dated candidate package from recent primary sources."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from podcast_contract import HOSTS, INTRO_EXACT, OUTRO_EXACT, expected_rubric, write_json

ROOT = Path("/root")
PROJECT = Path("/root/agentlabjournal")
NOTEBOOK = "fb0f2035-2378-47c1-9add-e7f27b223d56"
NOTEBOOKLM = "/root/.venvs/notebooklm/bin/notebooklm"
PRIMARY_DOMAINS = {
    "news.microsoft.com", "blogs.nvidia.com", "github.blog", "nist.gov", "www.nist.gov",
    "digital-strategy.ec.europa.eu", "ec.europa.eu", "duma.gov.ru", "aws.amazon.com",
}


def run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-4000:])
    return result.stdout


def extract_object(payload: dict) -> dict:
    answer = payload.get("answer", "")
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", answer, re.S)
    return json.loads(match.group(1) if match else answer.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--notebook", default=NOTEBOOK)
    parser.add_argument("--no-research", action="store_true")
    args = parser.parse_args()
    if not args.no_research:
        query = (
            f"Проверяемые AI/IT новости за предыдущие 24 часа к {args.date}. "
            "Только официальные блоги компаний, регуляторы и первичные документы; без агрегаторов и пересказов."
        )
        run([NOTEBOOKLM, "source", "add-research", query, "--mode", "fast", "--notebook", args.notebook, "--import-all"])
    sources = json.loads(run([NOTEBOOKLM, "source", "list", "--notebook", args.notebook, "--json"]))
    target = dt.date.fromisoformat(args.date)
    eligible = []
    for source in sources.get("sources", []):
        host = urlparse(source.get("url") or "").hostname
        created = source.get("created_at", "")[:10]
        if source.get("status") == "ready" and host in PRIMARY_DOMAINS and created in {args.date, (target - dt.timedelta(days=1)).isoformat()}:
            eligible.append({key: source.get(key) for key in ("id", "title", "url", "created_at")})
    if len(eligible) < 2:
        raise RuntimeError("RESEARCH_GATE: fewer than two recent primary sources")
    catalog = json.dumps(eligible[-20:], ensure_ascii=False)
    prompt = f"""Ты Research Agent. Выбери 2-3 новости за предыдущие 24 часа к {args.date} только из каталога ниже.
Верни только JSON с ключами news, daily_topic, listener_takeaway.
Каждая news: title, date YYYY-MM-DD, source_id, source_url, claim, why_it_matters, evidence_terms (3-4 точные строки из источника), qa_terms (3 коротких термина для транскрипта).
Не изменяй source_id/source_url. Не добавляй источники вне каталога. Не называй исследование одной компании универсальной статистикой.
Каталог: {catalog}
"""
    answer = json.loads(run([NOTEBOOKLM, "ask", "--notebook", args.notebook, "--new", "--yes", "--json", prompt]))
    selected = extract_object(answer)
    package = {
        "date": args.date, "language": "ru", "rubric": expected_rubric(args.date),
        "hosts": HOSTS, "intro_exact": INTRO_EXACT, "news": selected.get("news", []),
        "daily_topic": selected.get("daily_topic"), "listener_takeaway": selected.get("listener_takeaway"),
        "outro_exact": OUTRO_EXACT,
    }
    output = PROJECT / "podcasts/packages" / f"{args.date}-ru.candidate.json"
    write_json(output, package)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
