import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


audio = load("podcast_audio_producer_test", "podcast_audio_producer.py")
release = load("podcast_release_verifier_test", "podcast-release-verifier.py")


class PodcastResilienceTests(unittest.TestCase):
    def test_audio_terminal_failure_blocks_immediately(self):
        payload = json.dumps({"artifacts": [{"id": "a1", "status": "failed"}]})
        with mock.patch.object(audio, "run", return_value=payload):
            with self.assertRaisesRegex(RuntimeError, "terminal failure"):
                audio.wait_for_artifact("notebook", "a1", 300)

    def test_audio_missing_artifact_blocks_immediately(self):
        with mock.patch.object(audio, "run", return_value=json.dumps({"artifacts": []})):
            with self.assertRaisesRegex(RuntimeError, "Artifact missing"):
                audio.wait_for_artifact("notebook", "a1", 300)

    def test_release_network_error_still_writes_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff = root / "verifier.json"
            with mock.patch.object(release, "ROOT", root), \
                 mock.patch.object(release, "http", side_effect=OSError("offline")), \
                 mock.patch.object(release.urllib.request, "urlopen", side_effect=OSError("offline")), \
                 mock.patch.object(sys, "argv", ["verifier", "--date", "2026-08-10", "--handoff", str(handoff)]):
                self.assertEqual(release.main(), 1)
            payload = json.loads(handoff.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "FAIL")
            self.assertTrue(payload["errors"])

    def test_manual_yandex_confirmation_requires_public_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff = root / "verifier.json"
            with mock.patch.object(release, "ROOT", root), \
                 mock.patch.object(release, "http", return_value=200), \
                 mock.patch.object(release.urllib.request, "urlopen", side_effect=OSError("rss offline")), \
                 mock.patch.object(sys, "argv", ["verifier", "--date", "2026-08-10", "--handoff", str(handoff), "--yandex-confirmed"]):
                self.assertEqual(release.main(), 1)
            self.assertEqual(json.loads(handoff.read_text(encoding="utf-8"))["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
