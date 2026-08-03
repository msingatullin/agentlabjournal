#!/usr/bin/env python3
"""Validate measured source evidence before AgentLab article publication."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = ROOT / "seo-query-map.json"
ALLOWED_SOURCES = {"yandex-wordstat", "yandex-webmaster", "google-search-console", "approved-seo-dataset"}
MAX_AGE_DAYS = 90


def blocked(errors: list[str]) -> int:
    print("EVIDENCE_GATE: BLOCKED")
    for error in errors:
        print(f"- {error}")
    return 1


def source_path(evidence_ref: str) -> Path | None:
    match = re.match(r"^raw:([^#]+)", evidence_ref)
    if not match:
        return None
    return Path("/root/raw") / match.group(1)


def validate(slug: str, language: str) -> tuple[list[str], int]:
    try:
        data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read query map: {exc}"], 0
    base = data.get("articles", {}).get(slug)
    if not isinstance(base, dict):
        return [f"passport not found: {slug}"], 0
    passport = base if base.get("language") == language else {**base, **base.get("localizations", {}).get(language, {})}
    measurements = passport.get("measurements")
    if not isinstance(measurements, list) or not measurements:
        return ["measurements are required"], 0
    errors: list[str] = []
    verified = 0
    for index, row in enumerate(measurements, 1):
        prefix = f"measurement #{index}"
        row_errors: list[str] = []
        if not isinstance(row, dict):
            row_errors.append(f"{prefix}: must be an object")
            errors.extend(row_errors)
            continue
        if row.get("source") not in ALLOWED_SOURCES:
            row_errors.append(f"{prefix}: unsupported evidence source")
        ref = row.get("evidence_ref")
        path = source_path(ref) if isinstance(ref, str) else None
        if path is None or not path.is_file():
            row_errors.append(f"{prefix}: evidence file is missing or not a raw: reference ({ref!r})")
        measured_at = row.get("measured_at")
        try:
            age = (dt.date.today() - dt.date.fromisoformat(measured_at)).days
            if age < 0 or age > MAX_AGE_DAYS:
                row_errors.append(f"{prefix}: evidence date outside {MAX_AGE_DAYS}-day window")
        except (TypeError, ValueError):
            row_errors.append(f"{prefix}: measured_at must be YYYY-MM-DD")
        if row.get("frequency_value") is None or row.get("frequency_class") not in {"low", "medium", "high"}:
            row_errors.append(f"{prefix}: measured frequency and class are required")
        if not isinstance(row.get("metric"), str) or not row["metric"].strip():
            row_errors.append(f"{prefix}: metric is required")
        errors.extend(row_errors)
        if not row_errors:
            verified += 1
    return errors, verified


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--language", choices=("ru", "en"), default="ru")
    args = parser.parse_args()
    slug = re.sub(r"[^a-z0-9-]+", "-", args.slug.lower()).strip("-")
    errors, verified = validate(slug, args.language)
    if errors:
        return blocked(errors)
    print(f"EVIDENCE_GATE: OK ({slug}, {args.language}, {verified} verified measurements)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
