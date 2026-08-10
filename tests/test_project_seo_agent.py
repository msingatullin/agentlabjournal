import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProjectSeoAgentTests(unittest.TestCase):
    def test_registry_has_separate_project_agents_and_evidence_roots(self):
        registry = json.loads((ROOT / "seo-project-agents.json").read_text(encoding="utf-8"))["projects"]
        self.assertEqual(set(registry), {"agentlabjournal", "grifun", "microsrv", "sitevisor"})
        self.assertEqual(len({item["agent_id"] for item in registry.values()}), 4)
        self.assertEqual(len({item["raw_wordstat_root"] for item in registry.values()}), 4)
        self.assertTrue(all(item["status"] == "active" for item in registry.values()))
        self.assertTrue(all(item.get("parent_pillar_page") for item in registry.values()))

    def test_podcast_receives_measured_project_query_passport(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "passport.json"
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/project-seo-agent.py"),
                "--package", str(ROOT / "podcasts/packages/2026-08-10-ru.verified.json"),
                "--project-key", "agentlabjournal",
                "--canonical", "https://agentlabjournal.online/podcast-2026-08-10-ru.html",
                "--output", str(output),
            ])
            self.assertEqual(result.returncode, 0)
            passport = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(passport["seo_query_gate"], "OK")
            self.assertEqual(passport["evidence_source"], "yandex-wordstat")
            universe = json.loads((ROOT / "seo-keyword-universe.json").read_text(encoding="utf-8"))
            measured = {row["query"]: row for row in universe["keywords"]}
            self.assertIn(passport["primary_query"], measured)
            self.assertEqual(passport["frequency_value"], measured[passport["primary_query"]]["frequency_value"])
            self.assertTrue(passport["recommended_title"].startswith(passport["primary_query"].capitalize()))


if __name__ == "__main__":
    unittest.main()
