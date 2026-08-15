import json
import subprocess
import sys
import tempfile
import unittest
import datetime as dt
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from podcast_contract import build_generation_prompt, read_json, validate_episode_package
from podcast_transcript_qa import normalized, rubric_present, term_present
from podcast_fact_verifier import source_contains_date
from podcast_audio_producer import fallback_script
PLAN_SPEC = importlib.util.spec_from_file_location("daily_podcast_plan", ROOT / "scripts/daily-podcast-plan.py")
daily_podcast_plan = importlib.util.module_from_spec(PLAN_SPEC)
assert PLAN_SPEC.loader is not None
PLAN_SPEC.loader.exec_module(daily_podcast_plan)
source_date = daily_podcast_plan.source_date
exact_evidence_terms = daily_podcast_plan.exact_evidence_terms


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
        for item in package()["news"]:
            for term in item["qa_terms"]:
                self.assertIn(term, prompt)

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

    def test_source_date_uses_source_text_not_notebook_created_at(self):
        allowed = [dt.date(2026, 8, 10), dt.date(2026, 8, 9), dt.date(2026, 8, 8)]
        self.assertEqual(
            source_date("Submitted August 8, 2026", "https://example.invalid/a", allowed),
            (dt.date(2026, 8, 8), "source_text"),
        )

    def test_fact_verifier_accepts_european_date_format(self):
        self.assertTrue(source_contains_date("Updated 6 August 2026", dt.date(2026, 8, 6)))

    def test_observed_asr_equivalents_are_limited_and_accepted(self):
        self.assertTrue(term_present("в центре системы AI-Office", "ИИ-офис"))
        self.assertTrue(term_present("черновик NIST AI-202", "NIST AI 200-2"))
        self.assertTrue(term_present("анализ ирархических данных, в которых куча пропусков", "Иерархический анализ"))
        self.assertTrue(term_present("индивидуальная оценка на базе концепции ТВФ АТЛОН", "фреймворк ТЭВВ Атлон"))
        self.assertTrue(term_present("гибкие стандарты оценки систем", "оценка систем ИИ"))

    def test_source_date_rejects_unproven_date(self):
        allowed = [dt.date(2026, 8, 10), dt.date(2026, 8, 9), dt.date(2026, 8, 8)]
        self.assertEqual(source_date("no publication date", "https://example.invalid/a", allowed), (None, None))

    def test_exact_evidence_uses_claim_content_not_title_or_url(self):
        title = "AI Evaluation Framework"
        content = "\n".join([
            title,
            "https://example.invalid/framework",
            "The framework evaluates AI systems through repeatable testing and real-world impact assessment.",
            "Organizations can adapt the evaluation process to the risks of each deployed system.",
            "Independent validation records measurable evidence for governance decisions.",
        ])
        terms = exact_evidence_terms(content, "evaluation of AI systems and real-world impact", title)
        self.assertEqual(len(terms), 3)
        self.assertNotIn(title, terms)
        self.assertFalse(any(term.startswith("http") for term in terms))

    def test_72_hour_prompt_is_explicit(self):
        value = package()
        value["news_window_days"] = 3
        value["news_window_label"] = "Новости за последние 72 часа"
        self.assertIn("Новости за последние 72 часа", build_generation_prompt(value))

    def test_7_day_fallback_prompt_is_explicit(self):
        value = package()
        value["news_window_days"] = 7
        value["news_window_label"] = "Новости за последние 7 дней"
        self.assertIn("Новости за последние 7 дней", build_generation_prompt(value))

    def test_audio_fallback_script_preserves_contract(self):
        text = fallback_script(package())
        self.assertTrue(text.startswith(package()["intro_exact"]))
        self.assertTrue(text.endswith(package()["outro_exact"]))
        for item in package()["news"]:
            for term in item["qa_terms"]:
                self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
