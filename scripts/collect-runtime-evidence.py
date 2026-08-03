#!/usr/bin/env python3
"""Collect hash/status metadata for approved files and URLs; no content is copied."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "research-runs"

def file_item(value: str) -> dict:
    path = Path(value).expanduser()
    if not path.is_file():
        return {"type": "file", "path": value, "status": "missing"}
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"type": "file", "path": str(path), "status": "ok", "bytes": path.stat().st_size, "sha256": digest}

def url_item(value: str) -> dict:
    request = urllib.request.Request(value, method="HEAD", headers={"User-Agent": "AgentLabEvidence/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return {"type": "url", "url": value, "status": "ok", "http_status": response.status, "content_type": response.headers.get("Content-Type", "")}
    except Exception as exc:
        return {"type": "url", "url": value, "status": "error", "error": str(exc)[:500]}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--url", action="append", default=[])
    args = parser.parse_args()
    if not args.file and not args.url:
        print("RUNTIME_EVIDENCE: BLOCKED\n- provide at least one --file or --url")
        return 1
    run_id = args.run_id.replace("/", "-").replace("..", "-")
    out = RUNS / run_id / "runtime-evidence.json"
    items = [file_item(value) for value in args.file] + [url_item(value) for value in args.url]
    payload = {"schema_version": "1.0", "run_id": run_id, "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(), "items": items}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failed = sum(item["status"] != "ok" for item in items)
    print(f"RUNTIME_EVIDENCE: {'OK' if not failed else 'PARTIAL'} ({len(items)} items, {failed} failed)\n{out}")
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())
