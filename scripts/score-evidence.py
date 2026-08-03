#!/usr/bin/env python3
"""Score evidence provenance; score is a review aid, not proof by itself."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

WEIGHTS = {"official-doc": 0.95, "yandex-webmaster": 0.95, "google-search-console": 0.95, "yandex-wordstat": 0.9, "runtime-log": 0.9, "approved-dataset": 0.85, "screenshot": 0.5, "owner-report": 0.5}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"EVIDENCE_SCORE: BLOCKED\n- {exc}")
        return 1
    rows = report.get("evidence", [])
    if not isinstance(rows, list) or not rows:
        print("EVIDENCE_SCORE: BLOCKED\n- evidence list is empty")
        return 1
    scores = [WEIGHTS.get(row.get("source_type"), 0.3) for row in rows if isinstance(row, dict)]
    if not scores:
        print("EVIDENCE_SCORE: BLOCKED\n- evidence rows must be objects")
        return 1
    result = {"report": str(args.report), "evidence_count": len(scores), "scores": scores, "mean_score": round(sum(scores) / len(scores), 3), "source_weights": WEIGHTS}
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output: args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0

if __name__ == "__main__":
    sys.exit(main())
