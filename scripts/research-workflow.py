#!/usr/bin/env python3
"""Safe, metadata-only phase/checkpoint runner for AgentLab research runs."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "research-runs"
PHASES = ("discovery", "evidence", "experiment", "review", "delivery")
DEFAULT_BUDGETS = {phase: 1 for phase in PHASES}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_run_id(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-.")
    if not value:
        raise ValueError("run-id must contain letters, numbers, dot, underscore or dash")
    return value[:100]


def path_for(run_id: str) -> Path:
    return RUNS / safe_run_id(run_id) / "state.json"


def save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".state-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def load(run_id: str) -> tuple[Path, dict]:
    path = path_for(run_id)
    if not path.exists():
        raise ValueError(f"run not found: {run_id}")
    try:
        return path, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid checkpoint {path}: {exc}") from exc


def phase_index(phase: str) -> int:
    if phase not in PHASES:
        raise ValueError(f"unsupported phase: {phase}")
    return PHASES.index(phase)


def init(args: argparse.Namespace) -> int:
    path = path_for(args.run_id)
    if path.exists():
        return fail(f"refusing to overwrite existing run: {args.run_id}")
    state = {
        "schema_version": "1.0",
        "run_id": safe_run_id(args.run_id),
        "topic": args.topic,
        "created_at": now(),
        "updated_at": now(),
        "current_phase": PHASES[0],
        "review": {"status": "not_started", "notes": ""},
        "budgets": {phase: args.max_steps for phase in PHASES},
        "phases": {phase: {"status": "pending", "steps": 0, "evidence": [], "notes": ""} for phase in PHASES},
    }
    state["phases"][PHASES[0]]["status"] = "in_progress"
    save(path, state)
    print(json.dumps({"status": "created", "run": str(path.relative_to(ROOT))}, ensure_ascii=False))
    return 0


def complete(args: argparse.Namespace) -> int:
    path, state = load(args.run_id)
    target = phase_index(args.phase)
    current = phase_index(state["current_phase"])
    phase = state["phases"][args.phase]
    if target != current:
        return fail(f"phase order violation: current={state['current_phase']}, requested={args.phase}")
    if phase["status"] != "in_progress":
        return fail(f"phase is not in progress: {args.phase}")
    if phase["steps"] >= state["budgets"][args.phase]:
        return fail(f"step budget exhausted for phase: {args.phase}")
    if args.phase == "review" and not any(state["phases"][p]["evidence"] for p in PHASES[:3]):
        return fail("review requires at least one evidence reference")
    if args.phase == "delivery" and state["review"]["status"] != "passed":
        return fail("delivery requires review status passed")
    phase["steps"] += 1
    phase["status"] = "completed"
    phase["evidence"].extend(args.evidence)
    phase["notes"] = args.note
    if args.phase == "review":
        state["review"] = {"status": "passed", "notes": args.note, "at": now()}
    if target + 1 < len(PHASES):
        state["current_phase"] = PHASES[target + 1]
        state["phases"][PHASES[target + 1]]["status"] = "in_progress"
    else:
        state["current_phase"] = "complete"
    state["updated_at"] = now()
    save(path, state)
    print(json.dumps({"status": "completed", "phase": args.phase, "current_phase": state["current_phase"]}, ensure_ascii=False))
    return 0


def status(args: argparse.Namespace) -> int:
    path, state = load(args.run_id)
    print(json.dumps({"run": str(path.relative_to(ROOT)), **state}, ensure_ascii=False, indent=2))
    return 0


def fail(message: str) -> int:
    print(f"RESEARCH_WORKFLOW: BLOCKED\n- {message}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("init")
    create.add_argument("--run-id", required=True)
    create.add_argument("--topic", required=True)
    create.add_argument("--max-steps", type=int, default=1)
    create.set_defaults(func=init)
    finish = sub.add_parser("complete")
    finish.add_argument("--run-id", required=True)
    finish.add_argument("--phase", choices=PHASES, required=True)
    finish.add_argument("--evidence", action="append", default=[])
    finish.add_argument("--note", default="")
    finish.set_defaults(func=complete)
    show = sub.add_parser("status")
    show.add_argument("--run-id", required=True)
    show.set_defaults(func=status)
    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError) as exc:
        return fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
