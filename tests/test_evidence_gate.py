import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "scripts" / "evidence-gate.py"


def test_known_passport_has_real_evidence():
    result = subprocess.run([sys.executable, str(GATE), "--slug", "llm-function-calling-provider-comparison"], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_missing_passport_is_rejected():
    result = subprocess.run([sys.executable, str(GATE), "--slug", "missing-evidence-case"], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode != 0
    assert "EVIDENCE_GATE: BLOCKED" in result.stdout
