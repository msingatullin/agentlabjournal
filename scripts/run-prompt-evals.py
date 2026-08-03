#!/usr/bin/env python3
"""Deterministic runner for AgentLab prompt regression cases.

Without --responses this validates the eval manifest. With --responses it
checks JSONL records: {"id", "action", "text", "output"}.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "evals" / "agentlab-prompt-evals.json"


def fail(message: str) -> int:
    print(f"PROMPT_EVAL: FAIL\n- {message}")
    return 1


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc


def validate_manifest(data: dict) -> list[str]:
    errors = []
    if not isinstance(data.get("version"), str):
        errors.append("version is required")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        return ["cases must be a non-empty list"]
    ids = set()
    for index, case in enumerate(cases, 1):
        prefix = f"case #{index}"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{prefix} missing id")
        elif case_id in ids:
            errors.append(f"duplicate id: {case_id}")
        else:
            ids.add(case_id)
        if case.get("kind") not in {"control", "edge", "handoff", "output_contract"}:
            errors.append(f"{prefix} has unsupported kind")
        if not isinstance(case.get("expected_action"), str):
            errors.append(f"{prefix} missing expected_action")
        for key in ("must_include", "must_not_include", "required_json_fields"):
            if key in case and not isinstance(case[key], list):
                errors.append(f"{prefix} {key} must be a list")
    kinds = {case.get("kind") for case in cases if isinstance(case, dict)}
    for required in {"control", "edge", "handoff"}:
        if required not in kinds:
            errors.append(f"missing required case kind: {required}")
    return errors


def check_response(case: dict, response: dict) -> list[str]:
    errors = []
    if response.get("action") != case.get("expected_action"):
        errors.append(f"{case['id']}: expected action {case['expected_action']!r}, got {response.get('action')!r}")
    text = str(response.get("text", "")).casefold()
    for phrase in case.get("must_include", []):
        if phrase.casefold() not in text:
            errors.append(f"{case['id']}: missing required phrase {phrase!r}")
    for phrase in case.get("must_not_include", []):
        if phrase.casefold() in text:
            errors.append(f"{case['id']}: forbidden phrase present {phrase!r}")
    required = case.get("required_json_fields", [])
    if required:
        output = response.get("output")
        if not isinstance(output, dict):
            errors.append(f"{case['id']}: output object required")
        else:
            for field in required:
                if field not in output:
                    errors.append(f"{case['id']}: missing output field {field!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--responses", type=Path)
    args = parser.parse_args()
    try:
        manifest = load_json(args.manifest)
    except ValueError as exc:
        return fail(str(exc))
    errors = validate_manifest(manifest)
    if errors:
        return fail("; ".join(errors))
    cases = {case["id"]: case for case in manifest["cases"]}
    if args.responses:
        seen = set()
        try:
            lines = args.responses.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return fail(str(exc))
        for line_number, line in enumerate(lines, 1):
            try:
                response = json.loads(line)
            except json.JSONDecodeError as exc:
                return fail(f"responses line {line_number}: {exc}")
            case_id = response.get("id")
            if case_id not in cases:
                return fail(f"unknown response case: {case_id}")
            seen.add(case_id)
            errors.extend(check_response(cases[case_id], response))
        missing = set(cases) - seen
        if missing:
            errors.append(f"missing responses: {', '.join(sorted(missing))}")
    if errors:
        return fail("; ".join(errors))
    print(f"PROMPT_EVAL: OK ({len(cases)} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
