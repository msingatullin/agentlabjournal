#!/usr/bin/env python3
"""Submit one public canonical URL to Yandex.Webmaster recrawl and save evidence."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV_PATH = Path("/root/.config/yandex-webmaster.env")
RAW_DIR = Path("/root/raw/seo/yandex-webmaster")
API = "https://api.webmaster.yandex.net/v4"
EXPECTED_HOST = "agentlabjournal.online"


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def request_json(url: str, token: str, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Authorization": f"OAuth {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            error = json.load(exc)
        except (ValueError, json.JSONDecodeError):
            error = {"error_code": "HTTP_ERROR", "error_message": str(exc)}
        return exc.code, error


def write_evidence(event: dict) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    path = RAW_DIR / f"recrawl-{stamp}.json"
    with path.open("x", encoding="utf-8") as handle:
        json.dump(event, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    os.chmod(path, 0o600)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.url)
    if parsed.scheme != "https" or parsed.hostname != EXPECTED_HOST or parsed.query or parsed.fragment:
        print("RECRAWL: BLOCKED (URL must be a canonical Agent Lab HTTPS URL)", file=sys.stderr)
        return 2

    token = read_env().get("YANDEX_WEBMASTER_TOKEN")
    if not token:
        print("RECRAWL: BLOCKED (token missing)", file=sys.stderr)
        return 2
    status, user = request_json(f"{API}/user", token)
    if status != 200 or not user.get("user_id"):
        print(f"RECRAWL: BLOCKED (user lookup HTTP {status})", file=sys.stderr)
        return 3
    user_id = user["user_id"]
    status, host_data = request_json(f"{API}/user/{user_id}/hosts", token)
    if status != 200:
        print(f"RECRAWL: BLOCKED (host lookup HTTP {status})", file=sys.stderr)
        return 3
    host = next(
        (row for row in host_data.get("hosts", []) if urllib.parse.urlparse(row.get("ascii_host_url", "")).hostname == EXPECTED_HOST),
        None,
    )
    if not host or not host.get("verified"):
        print("RECRAWL: BLOCKED (verified host not found)", file=sys.stderr)
        return 3
    host_id = urllib.parse.quote(host["host_id"], safe="")
    quota_url = f"{API}/user/{user_id}/hosts/{host_id}/recrawl/quota"
    status, quota = request_json(quota_url, token)
    if status != 200:
        print(f"RECRAWL: BLOCKED (quota lookup HTTP {status})", file=sys.stderr)
        return 3
    if args.dry_run:
        print(json.dumps({"status": "dry-run-ok", "site": host["ascii_host_url"], "quota": quota}, ensure_ascii=False))
        return 0
    if int(quota.get("quota_remainder", 0)) <= 0:
        evidence_path = write_evidence({
            "submitted_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "site": host["ascii_host_url"], "url": args.url, "accepted": False,
            "quota_before": quota, "response": {"error_code": "DAILY_QUOTA_EXHAUSTED"},
        })
        print(f"RECRAWL: BLOCKED (quota exhausted; evidence {evidence_path})", file=sys.stderr)
        return 4

    queue_url = f"{API}/user/{user_id}/hosts/{host_id}/recrawl/queue"
    status, response = request_json(queue_url, token, method="POST", payload={"url": args.url})
    accepted = status in {201, 409} and (status != 409 or response.get("error_code") == "URL_ALREADY_ADDED")
    event = {
        "submitted_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "site": host["ascii_host_url"], "url": args.url, "accepted": accepted,
        "http_status": status, "quota_before": quota,
        "task_id": response.get("task_id"),
        "response_code": response.get("error_code", "CREATED" if status == 201 else "UNKNOWN"),
    }
    evidence_path = write_evidence(event)
    if not accepted:
        print(f"RECRAWL: BLOCKED (HTTP {status}; evidence {evidence_path})", file=sys.stderr)
        return 5
    print(json.dumps({
        "status": "accepted", "http_status": status, "url": args.url,
        "quota_before": quota, "task_id": response.get("task_id"), "evidence": str(evidence_path),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
