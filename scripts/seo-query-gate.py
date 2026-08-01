#!/usr/bin/env python3
"""Block article publication without an evidence-backed SEO query passport."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = ROOT / "seo-query-map.json"
FREQUENCY_CLASSES = {"low", "medium", "high"}
INTENTS = {"informational", "commercial", "transactional", "navigational", "mixed"}
SOURCES = {"yandex-wordstat", "yandex-webmaster", "google-search-console", "approved-seo-dataset"}
METRICS = {"monthly_searches", "impressions", "clicks"}


def fail(messages: list[str]) -> int:
    print("SEO_QUERY_GATE: BLOCKED")
    for message in messages:
        print(f"- {message}")
    return 1


def valid_http_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate(slug: str) -> list[str]:
    if not MAP_PATH.exists():
        return [f"missing query map: {MAP_PATH}"]
    try:
        data = json.loads(MAP_PATH.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read query map: {exc}"]

    passport = data.get("articles", {}).get(slug)
    if not isinstance(passport, dict):
        return [f"{slug}: query passport not found in {MAP_PATH.name}"]

    errors: list[str] = []
    required_text = (
        "primary_query", "intent", "region", "language", "target_url",
        "pillar_url", "cannibalization_evidence",
    )
    for key in required_text:
        if not isinstance(passport.get(key), str) or not passport[key].strip():
            errors.append(f"{slug}: missing {key}")

    if passport.get("intent") not in INTENTS:
        errors.append(f"{slug}: unsupported intent {passport.get('intent')!r}")
    if not valid_http_url(passport.get("target_url")):
        errors.append(f"{slug}: target_url must be an HTTPS URL")
    if not valid_http_url(passport.get("pillar_url")):
        errors.append(f"{slug}: pillar_url must be an HTTPS URL")
    expected_url = f"https://agentlabjournal.online/{slug}.html"
    if passport.get("target_url") != expected_url:
        errors.append(f"{slug}: target_url must equal {expected_url}")
    if passport.get("cannibalization_status") != "passed":
        errors.append(f"{slug}: cannibalization_status must be passed")

    internal_links = passport.get("internal_links")
    if not isinstance(internal_links, list) or not internal_links:
        errors.append(f"{slug}: internal_links must contain at least one target")
    elif not all(valid_http_url(item) for item in internal_links):
        errors.append(f"{slug}: every internal link must be an HTTPS URL")

    measurements = passport.get("measurements")
    if not isinstance(measurements, list) or not measurements:
        errors.append(f"{slug}: measurements are required")
        return errors

    observed_classes: set[str] = set()
    observed_queries: set[str] = set()
    today = dt.date.today()
    for index, row in enumerate(measurements, 1):
        prefix = f"{slug}: measurement #{index}"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        query = row.get("query")
        if not isinstance(query, str) or not query.strip():
            errors.append(f"{prefix} missing query")
        else:
            observed_queries.add(query.strip().casefold())
        frequency_class = row.get("frequency_class")
        if frequency_class not in FREQUENCY_CLASSES:
            errors.append(f"{prefix} frequency_class must be low, medium, or high")
        else:
            observed_classes.add(frequency_class)
        frequency = row.get("frequency_value")
        if not isinstance(frequency, int) or isinstance(frequency, bool) or frequency < 0:
            errors.append(f"{prefix} frequency_value must be a non-negative integer")
        if row.get("source") not in SOURCES:
            errors.append(f"{prefix} source must be an approved measured-data source")
        if row.get("metric") not in METRICS:
            errors.append(f"{prefix} metric must be monthly_searches, impressions, or clicks")
        for key in ("source", "metric", "measurement_period", "region", "match_type", "evidence_ref"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                errors.append(f"{prefix} missing {key}")
        measured_at = row.get("measured_at")
        try:
            measured_date = dt.date.fromisoformat(measured_at)
            if measured_date > today:
                errors.append(f"{prefix} measured_at is in the future")
            if (today - measured_date).days > 90:
                errors.append(f"{prefix} evidence is older than 90 days")
        except (TypeError, ValueError):
            errors.append(f"{prefix} measured_at must be YYYY-MM-DD")

    primary = str(passport.get("primary_query", "")).strip().casefold()
    if primary and primary not in observed_queries:
        errors.append(f"{slug}: primary_query has no measurement")
    for required_class in ("low", "high"):
        if required_class not in observed_classes:
            errors.append(f"{slug}: measurements must include a {required_class}-frequency query")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()
    slug = re.sub(r"[^a-z0-9-]+", "-", args.slug.lower()).strip("-")
    errors = validate(slug)
    if errors:
        return fail(errors)
    print(f"SEO_QUERY_GATE: OK ({slug})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
