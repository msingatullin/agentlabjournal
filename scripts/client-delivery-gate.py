#!/usr/bin/env python3
"""Allow client delivery only when a structured report and runtime artifacts exist."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

REQUIRED = ("question", "hypothesis", "method", "acceptance_criteria", "evidence", "results", "limitations", "decision")
DECISIONS = {"GO", "PARTIAL", "NO-GO"}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--runtime-evidence", type=Path, required=True)
    args = parser.parse_args()
    errors = []
    try: report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: errors.append(f"report unreadable: {exc}"); report = {}
    for key in REQUIRED:
        if not report.get(key): errors.append(f"missing report field: {key}")
    if report.get("decision") not in DECISIONS: errors.append("decision must be GO, PARTIAL or NO-GO")
    evidence = report.get("evidence", [])
    if not isinstance(evidence, list) or not evidence: errors.append("evidence list is empty")
    for index, row in enumerate(evidence if isinstance(evidence, list) else [], 1):
        if not isinstance(row, dict):
            errors.append(f"evidence #{index}: must be an object")
            continue
        for key in ("id", "source", "source_type", "collected_at", "claim"):
            if not row.get(key): errors.append(f"evidence #{index}: missing {key}")
    try: runtime = json.loads(args.runtime_evidence.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: errors.append(f"runtime evidence unreadable: {exc}"); runtime = {}
    items = runtime.get("items", [])
    if not items: errors.append("runtime evidence is empty")
    if any(item.get("status") != "ok" for item in items): errors.append("runtime evidence contains failed items")
    if errors:
        print("CLIENT_DELIVERY_GATE: BLOCKED")
        for error in errors: print(f"- {error}")
        return 1
    print(f"CLIENT_DELIVERY_GATE: OK ({report['decision']}, {len(evidence)} evidence items, {len(items)} runtime items)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
