import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SLUG = "anthropic-model-hardware-standard"


class MhsHomepageLeadTest(unittest.TestCase):
    def test_mhs_is_configured_and_rendered_as_homepage_lead(self):
        config = json.loads((ROOT / "homepage-editorial.json").read_text(encoding="utf-8"))
        homepage = (ROOT / "index.html").read_text(encoding="utf-8")
        lead = homepage.split('<article class="lead-story">', 1)[1].split("</article>", 1)[0]

        self.assertEqual(SLUG, config["lead"])
        self.assertIn(f'href="{SLUG}.html"', lead)
        self.assertIn("Model Hardware Standard", lead)
        self.assertIn("assets/news/anthropic-model-hardware-standard-20260827.png", lead)


if __name__ == "__main__":
    unittest.main()
