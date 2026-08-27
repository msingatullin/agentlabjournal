#!/usr/bin/env python3
"""Fail-closed state and validation for the Agent Lab Dzen newsroom."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import struct
import subprocess
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse


MIN_WIDTH = 1200
MIN_HEIGHT = 675
DUPLICATE_THRESHOLD = 0.88


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalized_story(package: dict) -> str:
    value = f"{package.get('title', '')} {package.get('body', '')}".casefold()
    value = re.sub(r"https?://\S+", " ", value)
    return re.sub(r"[^a-zа-яё0-9]+", " ", value).strip()


def image_dimensions(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()[:32]
    if data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    result = subprocess.run(
        ["identify", "-format", "%w %h", str(path)], text=True, capture_output=True
    )
    if result.returncode != 0:
        return None
    try:
        width, height = result.stdout.split()
        return int(width), int(height)
    except ValueError:
        return None


def verified_dzen_urls(registry: dict) -> set[str]:
    return {
        str(row.get("url"))
        for row in registry.get("articles", {}).values()
        if isinstance(row, dict) and row.get("verified") is True and row.get("url")
    }


def validate_package(package: dict, state: dict, registry: dict, query_map: dict, root: Path) -> list[str]:
    errors: list[str] = []
    if any(
        isinstance(row, dict) and row.get("id") == package.get("id")
        for row in state.get("items", [])
    ):
        errors.append("publication_id_exists")
    source = package.get("source") if isinstance(package.get("source"), dict) else {}
    if source.get("primary") is not True:
        errors.append("primary_source_missing")
    source_url = str(source.get("url") or "")
    if urlparse(source_url).scheme not in {"http", "https"}:
        errors.append("primary_source_url_invalid")
    evidence = root / str(source.get("evidence_path") or "")
    if not source.get("evidence_path") or not evidence.is_file():
        errors.append("source_evidence_missing")

    slug = str(package.get("seo_slug") or "")
    passport = query_map.get("articles", {}).get(slug)
    if not isinstance(passport, dict) or passport.get("cannibalization_status") != "passed":
        errors.append("query_passport_missing")

    image_path = root / str(package.get("image_path") or "")
    image_hash = ""
    if not image_path.is_file():
        errors.append("image_missing")
    else:
        dimensions = image_dimensions(image_path)
        if dimensions is None or dimensions[0] < MIN_WIDTH or dimensions[1] < MIN_HEIGHT:
            errors.append("image_dimensions_invalid")
        image_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()
    if not package.get("image_provenance"):
        errors.append("image_provenance_missing")

    body = str(package.get("body") or "")
    cta = str(package.get("cta_url") or "")
    if not cta or cta not in body or not cta.startswith("https://agentlabjournal.online/"):
        errors.append("site_cta_missing")

    related = package.get("related_dzen_urls") or []
    allowed_related = verified_dzen_urls(registry)
    if not related:
        errors.append("related_dzen_missing")
    elif any(url not in allowed_related or url not in body for url in related):
        errors.append("related_dzen_unverified")

    candidate = normalized_story(package)
    for existing in state.get("items", []):
        if not isinstance(existing, dict) or existing.get("id") == package.get("id"):
            continue
        if candidate and SequenceMatcher(None, candidate, normalized_story(existing)).ratio() >= DUPLICATE_THRESHOLD:
            errors.append("near_duplicate")
            break
    if image_hash:
        for existing in state.get("items", []):
            if not isinstance(existing, dict) or existing.get("id") == package.get("id"):
                continue
            existing_path = root / str(existing.get("image_path") or "")
            existing_hash = str(existing.get("image_sha256") or "")
            if not existing_hash and existing_path.is_file():
                existing_hash = hashlib.sha256(existing_path.read_bytes()).hexdigest()
            if existing_hash == image_hash:
                errors.append("image_reused")
                break
    return list(dict.fromkeys(errors))


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "enqueue"):
        child = sub.add_parser(command)
        child.add_argument("--root", type=Path, required=True)
        child.add_argument("--package", type=Path, required=True)
        child.add_argument("--state", type=Path, required=True)
        child.add_argument("--registry", type=Path, required=True)
        child.add_argument("--query-map", type=Path, required=True)
    due = sub.add_parser("due")
    due.add_argument("--state", type=Path, required=True)
    due.add_argument("--now", required=True)
    mark = sub.add_parser("mark-published")
    mark.add_argument("--state", type=Path, required=True)
    mark.add_argument("--id", required=True)
    mark.add_argument("--website-url", required=True)
    register = sub.add_parser("register-dzen-url")
    register.add_argument("--registry", type=Path, required=True)
    register.add_argument("--id", required=True)
    register.add_argument("--url", required=True)
    args = parser.parse_args()

    if args.command in {"validate", "enqueue"}:
        package = load_json(args.package)
        state = load_json(args.state)
        registry = load_json(args.registry)
        query_map = load_json(args.query_map)
        errors = validate_package(package, state, registry, query_map, args.root.resolve())
        print(json.dumps({"id": package.get("id"), "errors": errors}, ensure_ascii=False))
        if errors:
            return 1
        if args.command == "enqueue":
            image_path = args.root.resolve() / package["image_path"]
            package["image_sha256"] = hashlib.sha256(image_path.read_bytes()).hexdigest()
            package["content_hash"] = hashlib.sha256(normalized_story(package).encode()).hexdigest()
            state.setdefault("items", []).append(package)
            save_json(args.state, state)
        return 0

    if args.command == "due":
        state = load_json(args.state)
        now = parse_time(args.now)
        rows = [
            row for row in state.get("items", [])
            if row.get("status") == "queued" and parse_time(row["scheduled_at"]) <= now
        ]
        rows.sort(key=lambda row: (row["scheduled_at"], row["id"]))
        print(json.dumps(rows[0] if rows else {}, ensure_ascii=False))
        return 0

    if args.command == "mark-published":
        state = load_json(args.state)
        for row in state.get("items", []):
            if row.get("id") == args.id:
                row["status"] = "published"
                row["site_url"] = args.website_url
                save_json(args.state, state)
                return 0
        return 1

    registry = load_json(args.registry)
    if urlparse(args.url).netloc != "dzen.ru":
        return 1
    registry.setdefault("articles", {})[args.id] = {"url": args.url, "verified": True}
    save_json(args.registry, registry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
