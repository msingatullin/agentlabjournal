#!/usr/bin/env python3
"""Run exactly one podcast stage and write its own atomic handoff manifest."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True)
    parser.add_argument("--step", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--previous", required=True)
    parser.add_argument("--expect", action="append", default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    args.handoff_dir.mkdir(parents=True, exist_ok=True)
    output = args.handoff_dir / f"{args.step}-{args.agent}-output.json"
    base = {
        "stage": args.stage, "agent": args.agent,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "command": command,
    }
    try:
        start = json.loads((args.handoff_dir / "00-input.json").read_text(encoding="utf-8"))
        previous = json.loads((args.handoff_dir / args.previous).read_text(encoding="utf-8"))
        if previous.get("status") != "OK":
            raise RuntimeError(f"previous handoff is not OK: {args.previous}")
        if previous.get("run_id", start["run_id"]) != start["run_id"] or previous.get("date", start["date"]) != start["date"]:
            raise RuntimeError(f"previous handoff identity mismatch: {args.previous}")
        base.update({"run_id": start["run_id"], "date": start["date"]})
        result = subprocess.run(command, cwd="/root/agentlabjournal", text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout)[-4000:])
        artifacts = []
        for value in args.expect:
            path = Path(value)
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError(f"expected artifact missing: {path}")
            artifacts.append({"path": str(path), "bytes": path.stat().st_size, "sha256": digest(path)})
        stage_status = "OK"
        if args.agent == "release-verifier" and args.expect:
            verifier_payload = json.loads(Path(args.expect[0]).read_text(encoding="utf-8"))
            stage_status = verifier_payload.get("status", "FAIL")
        base.update({"status": stage_status, "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                     "artifacts": artifacts, "stdout": result.stdout[-2000:]})
        atomic_json(output, base)
        print(output)
        return 0
    except Exception as error:
        base.update({"status": "FAIL", "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(), "error": str(error)[:4000]})
        atomic_json(output, base)
        print(str(error), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
