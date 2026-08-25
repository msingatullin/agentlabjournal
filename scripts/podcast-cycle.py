#!/usr/bin/env python3
"""Generate, poll, download and validate NotebookLM podcast artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOK = "3a91cab6-c483-4a8c-aadf-24afb78d8d8a"
DEFAULT_POLL = 30
DEFAULT_TIMEOUT = 1800


def run_json(command: list[str]) -> dict:
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return json.loads(result.stdout)


def artifact_status(notebook: str, artifact_id: str) -> dict | None:
    data = run_json(["notebooklm", "artifact", "list", "--notebook", notebook, "--json"])
    return next((a for a in data.get("artifacts", []) if a.get("id") == artifact_id), None)


def validate_audio(path: Path) -> None:
    if not path.exists() or path.stat().st_size < 100_000:
        raise RuntimeError(f"audio file is missing or suspiciously small: {path}")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
        capture_output=True,
    )
    if probe.returncode != 0 or float(probe.stdout.strip() or 0) <= 1:
        raise RuntimeError(f"ffprobe rejected audio: {path}: {probe.stderr.strip()}")


def wait_for_completion(notebook: str, artifact_id: str, poll: int, timeout: int) -> dict:
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        artifact = artifact_status(notebook, artifact_id)
        if artifact is None:
            raise RuntimeError(f"artifact disappeared before completion: {artifact_id}")
        status = artifact.get("status")
        print(json.dumps({"event": "poll", "artifact_id": artifact_id, "status": status}, ensure_ascii=False), flush=True)
        if status == "completed":
            return artifact
        if status in {"failed", "error", "removed"}:
            raise RuntimeError(f"NotebookLM artifact failed: {artifact}")
        time.sleep(poll)
    raise TimeoutError(f"NotebookLM artifact timed out after {timeout}s: {artifact_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notebook", default=DEFAULT_NOTEBOOK)
    parser.add_argument("--artifact", required=True, help="Completed or pending NotebookLM audio artifact ID")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--poll", type=int, default=DEFAULT_POLL)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        wait_for_completion(args.notebook, args.artifact, args.poll, args.timeout)
        subprocess.run(
            ["notebooklm", "download", "audio", str(args.output), "--notebook", args.notebook, "--artifact", args.artifact],
            check=True,
        )
        validate_audio(args.output)
        print(json.dumps({"event": "completed", "artifact_id": args.artifact, "file": str(args.output), "bytes": args.output.stat().st_size, "completed_at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"event": "failed", "artifact_id": args.artifact, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
