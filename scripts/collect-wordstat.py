#!/usr/bin/env python3
"""Collect bounded, immutable Yandex Wordstat evidence for Agent Lab."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = Path("/root/.config/yandex-search-api.env")
DEFAULT_SEEDS = ROOT / "seo-seeds.json"
RAW_DIR = Path("/root/raw/seo/agentlab")
QUOTA_STATE = Path("/root/.cache/agentlab-wordstat-quota.json")
BASE_URL = "https://searchapi.api.cloud.yandex.net/v2/wordstat"
HOURLY_HARD_LIMIT = 90
MAX_REQUESTS_PER_RUN = 80


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def api_call(endpoint: str, payload: dict, key: str) -> dict:
    request = urllib.request.Request(
        f"{BASE_URL}/{endpoint}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Api-Key {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def find_region(nodes: list[dict], label: str) -> str | None:
    for node in nodes:
        if node.get("label") == label:
            return str(node["id"])
        found = find_region(node.get("children", []), label)
        if found:
            return found
    return None


def load_quota(now: dt.datetime) -> list[str]:
    if not QUOTA_STATE.exists():
        return []
    try:
        values = json.loads(QUOTA_STATE.read_text(encoding="utf-8")).get("requests", [])
    except (OSError, json.JSONDecodeError):
        return []
    cutoff = now - dt.timedelta(hours=1)
    return [value for value in values if dt.datetime.fromisoformat(value) > cutoff]


def save_quota(values: list[str]) -> None:
    QUOTA_STATE.parent.mkdir(parents=True, exist_ok=True)
    temp = QUOTA_STATE.with_suffix(".tmp")
    temp.write_text(json.dumps({"requests": values}, indent=2) + "\n", encoding="utf-8")
    os.chmod(temp, 0o600)
    temp.replace(QUOTA_STATE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--max-requests", type=int, default=MAX_REQUESTS_PER_RUN)
    args = parser.parse_args()
    if not 1 <= args.max_requests <= MAX_REQUESTS_PER_RUN:
        print(f"max requests must be between 1 and {MAX_REQUESTS_PER_RUN}", file=sys.stderr)
        return 2

    config = read_env(args.env)
    api_key = config.get("YANDEX_SEARCH_API_KEY")
    folder_id = config.get("YANDEX_CLOUD_FOLDER_ID")
    if not api_key or not folder_id:
        print("YANDEX_SEARCH_API_KEY or YANDEX_CLOUD_FOLDER_ID is missing", file=sys.stderr)
        return 2
    seed_data = json.loads(args.seeds.read_text(encoding="utf-8"))
    seeds = list(dict.fromkeys(str(value).strip() for value in seed_data["seeds"] if str(value).strip()))

    now = dt.datetime.now(dt.timezone.utc)
    quota = load_quota(now)
    required = 1 + len(seeds)
    allowed = min(args.max_requests, HOURLY_HARD_LIMIT - len(quota))
    if required > allowed:
        print(f"quota guard blocked: need {required}, allowed {allowed} in current hour", file=sys.stderr)
        return 3

    requests_used = 0

    def call(endpoint: str, payload: dict) -> dict:
        nonlocal requests_used, quota
        if requests_used >= args.max_requests or len(quota) >= HOURLY_HARD_LIMIT:
            raise RuntimeError("local quota guard reached")
        result = api_call(endpoint, payload, api_key)
        stamp = dt.datetime.now(dt.timezone.utc).isoformat()
        quota.append(stamp)
        save_quota(quota)
        requests_used += 1
        return result

    try:
        regions = call("getRegionsTree", {"folderId": folder_id})
        region_id = find_region(regions.get("regions", []), seed_data["region"])
        if not region_id:
            raise RuntimeError(f"region not found: {seed_data['region']}")
        observations = []
        for phrase in seeds:
            payload = {
                "folderId": folder_id,
                "phrase": phrase,
                "numPhrases": 250,
                "regions": [region_id],
                "devices": ["DEVICE_ALL"],
            }
            response = call("topRequests", payload)
            observations.append({
                "seed": phrase,
                "request": {key: value for key, value in payload.items() if key != "folderId"},
                "response": response,
            })
            time.sleep(0.12)
    except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError) as exc:
        print(f"collection failed after {requests_used} requests: {exc}", file=sys.stderr)
        return 4

    collected = dt.datetime.now(dt.timezone.utc)
    evidence = {
        "schema_version": 1,
        "project": seed_data["project"],
        "collected_at": collected.isoformat(),
        "measurement_period": "last 30 days",
        "region": {"id": region_id, "label": seed_data["region"]},
        "language": seed_data["language"],
        "source": {
            "provider": "Yandex Search API Wordstat",
            "documentation": "https://aistudio.yandex.ru/docs/ru/search-api/concepts/wordstat.html",
            "endpoint": f"{BASE_URL}/topRequests",
        },
        "requests_used": requests_used,
        "credentials_included": False,
        "observations": observations,
    }
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    timestamp = collected.strftime("%Y%m%d-%H%M%S")
    output = args.raw_dir / f"wordstat-{timestamp}.json"
    with output.open("x", encoding="utf-8") as handle:
        json.dump(evidence, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.chmod(output, 0o600)
    print(json.dumps({
        "status": "ok",
        "output": str(output),
        "requests_used": requests_used,
        "seeds": len(seeds),
        "region": seed_data["region"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
