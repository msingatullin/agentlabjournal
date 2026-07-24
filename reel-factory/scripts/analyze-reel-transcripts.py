#!/usr/bin/env python3
"""Extract a reusable, non-copying structure from short-video transcripts."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CTA_RE = re.compile(r"\b(подпис|переход|заход|покуп|приход|ссылк|коммент|спринт|курс|запис|скач|получ)\w*", re.I)
PROMISE_RE = re.compile(r"\b(как|помог|результат|получ|созда|сдела|заработ|науч|покаж)\w*", re.I)
PROOF_RE = re.compile(r"\b(аудитор|подписчик|участник|миллион|тысяч|день|месяц|результат|кейс)\w*", re.I)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def first_match(items: list[str], pattern: re.Pattern[str]) -> str | None:
    return next((item for item in items if pattern.search(item)), None)


def analyze(text: str, article_url: str | None = None) -> dict:
    clean = re.sub(r"\s+", " ", text).strip()
    parts = sentences(clean)
    words = clean.split()
    cta = [s for s in parts if CTA_RE.search(s)]
    evidence = [s for s in parts if PROOF_RE.search(s)]
    result = {
        "source_word_count": len(words),
        "source_sentence_count": len(parts),
        "structure": {
            "hook": parts[0] if parts else "",
            "promise": first_match(parts[:8], PROMISE_RE) or (parts[1] if len(parts) > 1 else ""),
            "proof_or_authority": evidence[:3],
            "method_steps": [s for s in parts if re.search(r"\b(сначала|затем|дальше|после|перв|втор|трет)\w*", s, re.I)][:6],
            "cta_examples": cta[-4:],
        },
        "production": {
            "estimated_seconds_at_150_wpm": round(len(words) / 150 * 60),
            "recommended_reel_seconds": "45-60",
            "recommended_scenes": 6,
            "speaker_pattern": "host -> expert -> host -> expert -> proof/B-roll -> CTA",
        },
        "originality_guardrails": [
            "Do not reuse source wording, examples, numbers, claims, or personal story.",
            "Keep only the abstract structure: hook, promise, proof, steps, CTA.",
            "Replace unsupported claims with evidence from our own article or mark them as hypotheses.",
            "Use one concrete Agent Lab Journal article as the destination.",
        ],
        "funnel": {
            "article_url": article_url or "",
            "tracked_url": (article_url + ("&" if article_url and "?" in article_url else "?") + "utm_source=instagram&utm_medium=reels&utm_campaign=agentlabjournal") if article_url else "",
            "cta_goal": "Перевести зрителя на статью и затем в форму заявки, не просить подписку без следующего шага.",
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--article-url")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = {str(path): analyze(path.read_text(encoding="utf-8"), args.article_url) for path in args.sources}
    output = json.dumps(payload if len(payload) > 1 else next(iter(payload.values())), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
