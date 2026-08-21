import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "refresh-homepage-editorial.py"


class RefreshHomepageEditorialTests(unittest.TestCase):
    def test_new_article_becomes_lead_and_timestamp_is_refreshed(self):
        spec = importlib.util.spec_from_file_location("refresh_editorial", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "homepage-editorial.json"
            path.write_text(json.dumps({
                "lead": "old-lead",
                "editors_choice": ["a", "b", "c"],
                "deep_reads": ["d", "e"],
                "updated_at": "2026-08-09T05:26:47+03:00",
                "owner": "homepage-editor",
            }))
            module.refresh(path, "new-article", now="2026-08-21T23:30:00+03:00")
            result = json.loads(path.read_text())
        self.assertEqual("new-article", result["lead"])
        self.assertEqual("2026-08-21T23:30:00+03:00", result["updated_at"])
        self.assertEqual(["a", "b", "c"], result["editors_choice"])


if __name__ == "__main__":
    unittest.main()
