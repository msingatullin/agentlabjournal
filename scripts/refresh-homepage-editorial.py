#!/usr/bin/env python3
"""Refresh homepage curation when a new canonical article is selected."""
from argparse import ArgumentParser
from datetime import datetime
import json
from pathlib import Path


def refresh(path: Path, slug: str, now: str | None = None) -> None:
    config = json.loads(path.read_text(encoding="utf-8"))
    config["lead"] = slug
    config["updated_at"] = now or datetime.now().astimezone().isoformat(timespec="seconds")
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--slug", required=True)
    args = parser.parse_args()
    refresh(args.file, args.slug)


if __name__ == "__main__":
    main()
