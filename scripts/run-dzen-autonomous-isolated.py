#!/usr/bin/env python3
"""Run one autonomous Dzen cycle from a clean disposable clone."""
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import tempfile
from pathlib import Path


REMOTE = "git@github.com:msingatullin/agentlabjournal.git"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="agentlab-dzen-") as directory:
        checkout = Path(directory) / "repo"
        clone = subprocess.run(["git", "clone", "--depth", "1", REMOTE, str(checkout)])
        if clone.returncode:
            return clone.returncode
        if args.dry_run:
            stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            receipt = Path("/var/lib/agentlab-dzen") / f"dry-run-{stamp}.json"
        else:
            receipt = Path("/var/lib/agentlab-dzen/last-receipt.json")
        receipt.parent.mkdir(parents=True, exist_ok=True)
        command = [
            "/usr/bin/python3",
            str(checkout / "scripts" / "dzen-article-pipeline.py"),
            "autonomous",
            "--root",
            str(checkout),
            "--receipt",
            str(receipt),
        ]
        if args.dry_run:
            command.append("--dry-run")
        return subprocess.run(command, cwd=checkout).returncode


if __name__ == "__main__":
    raise SystemExit(main())
