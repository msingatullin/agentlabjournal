#!/usr/bin/env python3
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dzen-newsroom.py"
RELATED = "https://dzen.ru/a/anBOmaf6jAN4CHtI"


def png(width: int = 1600, height: int = 900, marker: bytes = b"") -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height) + marker


class DzenNewsroomTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "evidence.json").write_text('{"source":"official"}\n', encoding="utf-8")
        (self.root / "cover.png").write_bytes(png())
        self.package = {
            "id": "news-20260827-001",
            "title": "Компания представила проверяемый инструмент для бизнеса",
            "body": (
                "Компания выпустила новый инструмент и описала условия запуска. "
                "Разбираем, что изменилось, кому это полезно и какие ограничения пока остаются. "
                "Подробнее на сайте: https://agentlabjournal.online/guides.html "
                f"Связанный материал в Дзене: {RELATED}"
            ),
            "source": {
                "url": "https://example.org/official-release",
                "publisher": "Example",
                "published_at": "2026-08-27T18:00:00+03:00",
                "evidence_path": "evidence.json",
                "primary": True,
            },
            "seo_slug": "verified-news",
            "image_path": "cover.png",
            "image_provenance": "generated-editorial",
            "site_url": "https://agentlabjournal.online/verified-news.html",
            "cta_url": "https://agentlabjournal.online/guides.html",
            "related_dzen_urls": [RELATED],
            "scheduled_at": "2026-08-28T08:00:00+03:00",
            "status": "queued",
        }
        self.state = {"items": []}
        self.registry = {"articles": {"canary": {"url": RELATED, "verified": True}}}
        self.query_map = {"articles": {"verified-news": {"primary_query": "ии для бизнеса", "cannibalization_status": "passed"}}}

    def tearDown(self):
        self.temp.cleanup()

    def validate(self, package=None, state=None):
        package_path = self.root / "package.json"
        state_path = self.root / "state.json"
        registry_path = self.root / "registry.json"
        query_path = self.root / "query.json"
        package_path.write_text(json.dumps(package or self.package, ensure_ascii=False), encoding="utf-8")
        state_path.write_text(json.dumps(state or self.state, ensure_ascii=False), encoding="utf-8")
        registry_path.write_text(json.dumps(self.registry, ensure_ascii=False), encoding="utf-8")
        query_path.write_text(json.dumps(self.query_map, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            ["python3", str(SCRIPT), "validate", "--root", str(self.root), "--package", str(package_path),
             "--state", str(state_path), "--registry", str(registry_path), "--query-map", str(query_path)],
            text=True, capture_output=True,
        )
        return result, json.loads(result.stdout) if result.stdout.strip().startswith("{") else {}

    def test_valid_package_passes(self):
        result, payload = self.validate()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([], payload["errors"])

    def test_rejects_near_duplicate_story(self):
        state = {"items": [{**self.package, "id": "older", "site_url": "https://agentlabjournal.online/older.html"}]}
        result, payload = self.validate(state=state)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("near_duplicate", payload["errors"])

    def test_rejects_missing_primary_evidence(self):
        package = {**self.package, "source": {**self.package["source"], "primary": False}}
        _, payload = self.validate(package=package)
        self.assertIn("primary_source_missing", payload["errors"])

    def test_rejects_missing_query_passport(self):
        package = {**self.package, "seo_slug": "unknown"}
        _, payload = self.validate(package=package)
        self.assertIn("query_passport_missing", payload["errors"])

    def test_rejects_reused_image(self):
        state = {"items": [{**self.package, "id": "older", "title": "Другая тема", "body": "Совершенно другой материал"}]}
        _, payload = self.validate(state=state)
        self.assertIn("image_reused", payload["errors"])

    def test_rejects_small_image(self):
        (self.root / "cover.png").write_bytes(png(700, 400))
        _, payload = self.validate()
        self.assertIn("image_dimensions_invalid", payload["errors"])

    def test_rejects_missing_site_cta(self):
        package = {**self.package, "body": self.package["body"].replace(self.package["cta_url"], "")}
        _, payload = self.validate(package=package)
        self.assertIn("site_cta_missing", payload["errors"])

    def test_rejects_unregistered_dzen_link(self):
        package = {**self.package, "related_dzen_urls": ["https://dzen.ru/a/unknown"]}
        _, payload = self.validate(package=package)
        self.assertIn("related_dzen_unverified", payload["errors"])

    def test_enqueue_is_idempotent_for_stable_publication_id(self):
        package_path = self.root / "package.json"
        state_path = self.root / "state.json"
        registry_path = self.root / "registry.json"
        query_path = self.root / "query.json"
        package_path.write_text(json.dumps(self.package, ensure_ascii=False), encoding="utf-8")
        state_path.write_text(json.dumps(self.state), encoding="utf-8")
        registry_path.write_text(json.dumps(self.registry), encoding="utf-8")
        query_path.write_text(json.dumps(self.query_map, ensure_ascii=False), encoding="utf-8")
        command = [
            "python3", str(SCRIPT), "enqueue", "--root", str(self.root), "--package", str(package_path),
            "--state", str(state_path), "--registry", str(registry_path), "--query-map", str(query_path),
        ]
        first = subprocess.run(command, text=True, capture_output=True)
        second = subprocess.run(command, text=True, capture_output=True)
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertNotEqual(0, second.returncode)
        self.assertEqual(1, len(json.loads(state_path.read_text())["items"]))


if __name__ == "__main__":
    unittest.main()
