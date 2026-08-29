#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dzen-article-pipeline.py"
spec = importlib.util.spec_from_file_location("dzen_article_pipeline", SCRIPT)
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class DzenArticlePipelineTest(unittest.TestCase):
    def setUp(self):
        self.draft = "Полный проверяемый черновик статьи."
        self.digest = pipeline.draft_sha256(self.draft)
        self.review = {
            "reviewed_draft_sha256": self.digest,
            "verdict": "APPROVE",
            "score_0_100": 86,
            "blocking_issues": [],
            "revision_instructions": [],
            "citations": [{"source_id": "official-dzen", "citation_number": 1}],
        }

    def test_approve_requires_matching_hash_score_and_citations(self):
        self.assertEqual(pipeline.validate_review(self.review, self.digest), [])

    def test_malformed_or_hash_mismatched_review_fails_closed(self):
        bad = {**self.review, "reviewed_draft_sha256": "0" * 64}
        self.assertIn("reviewed_draft_hash_mismatch", pipeline.validate_review(bad, self.digest))
        self.assertIn("review_missing_citations", pipeline.validate_review({"verdict": "APPROVE"}, self.digest))

    def test_fourth_revision_is_dead_letter(self):
        state = {"status": "REVISE", "revision_attempts": 3}
        result = pipeline.transition(state, {**self.review, "verdict": "REVISE", "score_0_100": 70})
        self.assertEqual(result["status"], "DEAD_LETTER")

    def test_daily_release_limit_and_no_catch_up(self):
        state = {"published_dates": ["2026-08-29"]}
        self.assertFalse(pipeline.can_publish_today(state, datetime.fromisoformat("2026-08-29T20:00:00+03:00")))
        self.assertTrue(pipeline.can_publish_today(state, datetime.fromisoformat("2026-08-30T00:00:00+03:00")))

    def test_review_prompt_contains_immutable_inputs(self):
        prompt = pipeline.build_review_prompt(
            self.draft,
            self.digest,
            {"sources": [{"url": "https://dzen.ru/help/ru/requirements/rules.html"}]},
            {"scene": "Инженер проверяет автономный агент"},
        )
        for value in (self.draft, self.digest, "requirements/rules.html", "Инженер проверяет"):
            self.assertIn(value, prompt)

    def test_reused_image_url_or_hash_is_blocked(self):
        registry = {"items": [{"image_url": "https://example/a.png", "image_sha256": "abc"}]}
        self.assertIn("image_url_reused", pipeline.validate_unique_image("https://example/a.png", "def", registry))
        self.assertIn("image_hash_reused", pipeline.validate_unique_image("https://example/b.png", "abc", registry))

    def test_dry_run_writes_receipt_without_external_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            (package / "draft-v1.md").write_text(self.draft, encoding="utf-8")
            (package / "sources-context.json").write_text(json.dumps({"sources": []}), encoding="utf-8")
            (package / "image-brief.json").write_text(json.dumps({"scene": "test"}), encoding="utf-8")
            receipt = pipeline.dry_run(package)
            self.assertEqual(receipt["mode"], "dry-run")
            self.assertEqual(receipt["external_actions"], [])
            self.assertTrue((package / "dry-run-receipt.json").is_file())

    def test_systemd_timer_runs_every_four_hours_without_catch_up(self):
        timer = (ROOT / "ops/systemd/agentlab-dzen-article-pipeline.timer").read_text()
        service = (ROOT / "ops/systemd/agentlab-dzen-article-pipeline.service").read_text()
        self.assertIn("OnCalendar=*-*-* 00/4:00:00 Europe/Moscow", timer)
        self.assertIn("Persistent=false", timer)
        self.assertIn("run-dzen-autonomous-isolated.py", service)
        self.assertIn("/usr/bin/flock -n", service)

    def test_installer_requires_two_matching_dry_run_receipts(self):
        installer = (ROOT / "scripts/install-dzen-article-pipeline.sh").read_text()
        self.assertIn("DRY_RUN_RECEIPTS_REQUIRED=2", installer)
        self.assertIn("disable --now hermes-dzen-send.timer", installer)
        self.assertIn("systemd-analyze verify", installer)

    def test_autonomous_command_uses_isolated_codex_and_machine_readable_receipt(self):
        command = pipeline.build_codex_command(Path("/tmp/isolated"), Path("/tmp/receipt.json"), dry_run=True)
        self.assertEqual(command[0:2], ["/usr/bin/codex", "exec"])
        self.assertIn("--ephemeral", command)
        self.assertIn("danger-full-access", command)
        self.assertIn("--output-schema", command)
        self.assertEqual(command[-1], "-")

    def test_autonomous_prompt_requires_all_publication_gates(self):
        prompt = pipeline.build_autonomous_prompt(dry_run=False)
        for required in (
            "Wordstat",
            pipeline.NOTEBOOK_ID,
            "score_0_100 >= 80",
            "unique",
            "dzen-rss.xml",
            "git push",
            "Yandex.Webmaster",
            "one publication per Moscow calendar day",
        ):
            self.assertIn(required, prompt)

    def test_publication_slot_is_fail_closed_until_next_moscow_day(self):
        state = {"last_published_at": "2026-08-29T02:00:00+03:00"}
        self.assertFalse(pipeline.publication_slot_open(state, datetime.fromisoformat("2026-08-29T23:59:00+03:00")))
        self.assertTrue(pipeline.publication_slot_open(state, datetime.fromisoformat("2026-08-30T00:00:00+03:00")))


if __name__ == "__main__":
    unittest.main()
