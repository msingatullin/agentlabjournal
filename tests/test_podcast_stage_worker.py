import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "scripts/podcast-stage-worker.py"


class PodcastStageWorkerTests(unittest.TestCase):
    def test_success_requires_previous_handoff_and_hashes_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "00-input.json").write_text(json.dumps({"run_id": "run-1", "date": "2026-08-09"}))
            (root / "01-dispatcher-output.json").write_text(json.dumps({"status": "OK"}))
            artifact = root / "candidate.json"
            command = [sys.executable, "-c", f"from pathlib import Path; Path({str(artifact)!r}).write_text('ok')"]
            result = subprocess.run([sys.executable, str(WORKER), "--stage", "Research Agent", "--step", "02",
                "--agent", "research", "--handoff-dir", str(root), "--previous", "01-dispatcher-output.json",
                "--expect", str(artifact), "--", *command])
            self.assertEqual(result.returncode, 0)
            payload = json.loads((root / "02-research-output.json").read_text())
            self.assertEqual(payload["status"], "OK")
            self.assertEqual(len(payload["artifacts"][0]["sha256"]), 64)

    def test_missing_previous_handoff_blocks_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "00-input.json").write_text(json.dumps({"run_id": "run-1", "date": "2026-08-09"}))
            marker = root / "must-not-exist"
            result = subprocess.run([sys.executable, str(WORKER), "--stage", "Fact Verification Agent", "--step", "03",
                "--agent", "fact-verification", "--handoff-dir", str(root), "--previous", "02-research-output.json",
                "--", sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"])
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            payload = json.loads((root / "03-fact-verification-output.json").read_text())
            self.assertEqual(payload["status"], "FAIL")

    def test_previous_handoff_identity_mismatch_blocks_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "00-input.json").write_text(json.dumps({"run_id": "run-a", "date": "2026-08-10"}))
            (root / "01-dispatcher-output.json").write_text(json.dumps({"status": "OK", "run_id": "run-b", "date": "2026-08-10"}))
            marker = root / "must-not-exist"
            result = subprocess.run([
                sys.executable, str(WORKER), "--stage", "Research Agent", "--step", "02",
                "--agent", "research", "--handoff-dir", str(root), "--previous", "01-dispatcher-output.json",
                "--", sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()",
            ])
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())
            payload = json.loads((root / "02-research-output.json").read_text())
            self.assertIn("identity mismatch", payload["error"])

    def test_release_verifier_preserves_blocked_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "00-input.json").write_text(json.dumps({"run_id": "run-a", "date": "2026-08-10"}))
            (root / "08-publisher-output.json").write_text(json.dumps({"status": "OK", "run_id": "run-a", "date": "2026-08-10"}))
            artifact = root / "verifier.json"
            command = [sys.executable, "-c", f"from pathlib import Path; Path({str(artifact)!r}).write_text({json.dumps(json.dumps({'status': '[BLOCKED: Yandex indexing unconfirmed]'}))})"]
            result = subprocess.run([sys.executable, str(WORKER), "--stage", "Release Verifier Agent", "--step", "09",
                "--agent", "release-verifier", "--handoff-dir", str(root), "--previous", "08-publisher-output.json",
                "--expect", str(artifact), "--", *command])
            self.assertEqual(result.returncode, 0)
            payload = json.loads((root / "09-release-verifier-output.json").read_text())
            self.assertEqual(payload["status"], "[BLOCKED: Yandex indexing unconfirmed]")


if __name__ == "__main__":
    unittest.main()
