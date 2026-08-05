#!/usr/bin/env python3
"""Generate and download audio from an approved podcast production package."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from podcast_contract import read_json, write_json

NOTEBOOKLM = "/root/.venvs/notebooklm/bin/notebooklm"
DEFAULT_NOTEBOOK = "fb0f2035-2378-47c1-9add-e7f27b223d56"


def run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-4000:])
    return result.stdout.strip()


def wait_for_artifact(notebook: str, artifact_id: str, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        payload = json.loads(run([NOTEBOOKLM, "artifact", "list", "--notebook", notebook, "--json"]))
        artifact = next((item for item in payload.get("artifacts", []) if item.get("id") == artifact_id), None)
        if artifact and artifact.get("status") == "completed":
            return
        time.sleep(30)
    raise TimeoutError(f"Artifact timeout: {artifact_id}")


def ensure_mp3(path: Path) -> None:
    probe = run(["ffprobe", "-v", "error", "-show_entries", "format=format_name", "-of", "default=nw=1:nk=1", str(path)])
    if probe == "mp3":
        return
    converted = path.with_suffix(".converted.mp3")
    subprocess.run(["ffmpeg", "-y", "-i", str(path), "-codec:a", "libmp3lame", "-b:a", "192k", str(converted)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    converted.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--notebook", default=DEFAULT_NOTEBOOK)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    package = read_json(args.package)
    if package.get("editorial_gate", {}).get("status") != "passed" or not package.get("production_prompt"):
        raise ValueError("EDITORIAL_GATE: BLOCKED")
    command = [NOTEBOOKLM, "generate", "audio", package["production_prompt"], "--notebook", args.notebook]
    for item in package["news"]:
        command.extend(["--source", item["source_id"]])
    command.extend(["--format", "deep-dive", "--length", "default", "--language", "ru", "--retry", "2", "--json"])
    payload = json.loads(run(command))
    artifact_id = payload.get("task_id") or payload.get("artifact_id") or payload.get("id")
    if not artifact_id:
        raise RuntimeError(f"No artifact id: {payload}")
    state = {"status": "generating", "artifact_id": artifact_id, "package": str(args.package)}
    write_json(args.state, state)
    wait_for_artifact(args.notebook, artifact_id, args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([NOTEBOOKLM, "download", "audio", str(args.output), "--notebook", args.notebook, "--artifact", artifact_id, "--force"], check=True)
    ensure_mp3(args.output)
    if args.output.stat().st_size < 100_000:
        raise RuntimeError("Audio is suspiciously small")
    state.update({"status": "audio_ready", "audio": str(args.output), "bytes": args.output.stat().st_size})
    write_json(args.state, state)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
