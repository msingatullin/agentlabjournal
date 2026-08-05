import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from podcast_contract import build_generation_prompt, read_json, validate_episode_package
from podcast_transcript_qa import normalized, rubric_present


def package() -> dict:
    payload = read_json(ROOT / "podcasts/packages/2026-08-05-ru.verified.json")
    validate_episode_package(payload)
    return payload


class PodcastPipelineTests(unittest.TestCase):
    def test_asr_normalization_preserves_required_identity_and_rubric(self):
        self.assertEqual(normalized("Артём"), normalized("Артем"))
        self.assertTrue(rubric_present("Наша рубрика Человек в эс Машина", "Человек vs Машина"))

    def test_prompt_contains_every_required_block(self):
        prompt = build_generation_prompt(package())
        for required in (
            "Артём", "Мира", "Agent Lab Journal Podcast", "Новости за последние 24 часа",
            "Человек vs Машина", "Microsoft", "NVIDIA", "GitHub", "agentlabjournal.online",
        ):
            self.assertIn(required, prompt)

    def test_qa_blocks_missing_intro(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            transcript = temp / "bad.txt"
            transcript.write_text("Новости за последние 24 часа. Microsoft NVIDIA GitHub. Человек vs Машина.", encoding="utf-8")
            audio = temp / "audio.mp3"
            audio.write_bytes(b"0" * 100_001)
            manifest = temp / "qa.json"
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/podcast_transcript_qa.py"),
                "--package", str(ROOT / "podcasts/packages/2026-08-05-ru.production.json"),
                "--transcript", str(transcript), "--audio", str(audio), "--output", str(manifest),
            ])
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
