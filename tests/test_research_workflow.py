import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "research-workflow.py"


def run(*args):
    return subprocess.run([sys.executable, str(RUNNER), *args], cwd=ROOT, text=True, capture_output=True)


def test_checkpoint_order_and_review(tmp_path):
    run_id = f"test-{tmp_path.name}"
    created = run("init", "--run-id", run_id, "--topic", "test")
    assert created.returncode == 0, created.stdout
    assert run("complete", "--run-id", run_id, "--phase", "evidence", "--evidence", "source.txt").returncode == 1
    assert run("complete", "--run-id", run_id, "--phase", "discovery", "--evidence", "source.txt").returncode == 0
    assert run("complete", "--run-id", run_id, "--phase", "evidence", "--evidence", "source.txt").returncode == 0
    assert run("complete", "--run-id", run_id, "--phase", "experiment", "--evidence", "result.json").returncode == 0
    assert run("complete", "--run-id", run_id, "--phase", "review", "--note", "reviewed").returncode == 0
    assert run("complete", "--run-id", run_id, "--phase", "delivery").returncode == 0
    state = json.loads((ROOT / "research-runs" / run_id / "state.json").read_text())
    assert state["current_phase"] == "complete"
