#!/usr/bin/env python3
"""Block podcast publication unless the transcript satisfies the episode contract."""
from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

from podcast_contract import read_json, write_json


def normalized(value: str) -> str:
    return re.sub(r"[^a-zа-яё0-9]+", " ", value.casefold().replace("ё", "е")).strip()


def contains_all(text: str, words: list[str]) -> bool:
    value = normalized(text)
    return all(normalized(word) in value for word in words)


def contains_any(text: str, variants: list[str]) -> bool:
    value = normalized(text)
    return any(normalized(variant) in value for variant in variants)


def rubric_present(text: str, rubric: str) -> bool:
    variants = [rubric]
    if " vs " in f" {rubric.casefold()} ":
        variants.extend(
            [
                re.sub(r"\bvs\b", "ви эс", rubric, flags=re.IGNORECASE),
                re.sub(r"\bvs\b", "в эс", rubric, flags=re.IGNORECASE),
            ]
        )
    return contains_any(text, variants)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = read_json(args.package)
    transcript = args.transcript.read_text(encoding="utf-8")
    checks = {
        "brand_intro": contains_all(transcript[:2500], ["Артём", "Мира"]) and contains_any(
            transcript[:2500],
            [
                "Agent Lab Journal Podcast",
                "Agent Lab Journal подкаст",
                "Агент Лаб Журнал Подкаст",
            ],
        ),
        "daily_news_block": contains_all(transcript, ["новости", "последние 24 часа"]),
        "rubric": rubric_present(transcript, package["rubric"]),
        "all_news": all(contains_all(transcript, item["qa_terms"]) for item in package["news"]),
        "practical_actions": contains_all(transcript, ["первое", "второе", "третье"]),
        "outro": contains_any(transcript[-3000:], ["AgentLab", "Агент Лаб"]) and contains_all(
            transcript[-3000:], ["автоматизировать процессы"]
        ) and contains_any(transcript[-3000:], ["agentlabjournal.online", "агент лаб журнал точка онлайн"]),
        "audio_exists": args.audio.is_file() and args.audio.stat().st_size >= 100_000,
    }
    status = "passed" if all(checks.values()) else "blocked"
    manifest = {
        "status": status, "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "package": str(args.package), "transcript": str(args.transcript), "audio": str(args.audio), "checks": checks,
    }
    write_json(args.output, manifest)
    print(args.output)
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
