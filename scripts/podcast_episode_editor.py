#!/usr/bin/env python3
"""Compile a fact-verified package into a locked NotebookLM production brief."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from podcast_contract import build_generation_prompt, read_json, validate_episode_package, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = read_json(args.input)
    if package.get("fact_gate", {}).get("status") != "passed":
        raise ValueError("FACT_GATE: BLOCKED")
    validate_episode_package(package)
    package["production_prompt"] = build_generation_prompt(package)
    package["editorial_gate"] = {"status": "passed", "checked_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    write_json(args.output, package)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
