import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run-prompt-evals.py"
MANIFEST = ROOT / "evals" / "agentlab-prompt-evals.json"


def test_manifest_passes():
    result = subprocess.run([sys.executable, str(RUNNER), "--manifest", str(MANIFEST)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_response_contract_passes(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for case in manifest["cases"]:
        row = {"id": case["id"], "action": case["expected_action"], "text": " ".join(case.get("must_include", []))}
        if case.get("required_json_fields"):
            row["output"] = {field: "present" for field in case["required_json_fields"]}
        rows.append(json.dumps(row, ensure_ascii=False))
    responses = tmp_path / "responses.jsonl"
    responses.write_text("\n".join(rows) + "\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(RUNNER), "--responses", str(responses)], text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
