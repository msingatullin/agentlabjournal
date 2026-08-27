import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "refresh-homepage-latest.py"


def load_module():
    spec = importlib.util.spec_from_file_location("refresh_homepage_latest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RefreshHomepageLatestTest(unittest.TestCase):
    def test_updates_only_issue_date_and_latest_list(self):
        page = '''<head><meta name="takprodam-verification" content="keep"></head>
<div class="issue-line"><time datetime="2026-08-21">21 августа 2026</time><span>Journal</span></div>
<section class="search-panel">KEEP SEARCH</section>
<aside class="latest-rail"><div><h2>Новое</h2></div><ol><li>OLD</li></ol></aside>
<script>KEEP FILTERS</script>'''
        items = [{"path": "new.html", "title": "Новый материал", "created": "2026-08-27"}]
        with tempfile.NamedTemporaryFile("w+", suffix=".html", encoding="utf-8") as target:
            target.write(page)
            target.flush()
            module = load_module()
            module.refresh(Path(target.name), items, issue_date="2026-08-27")
            result = Path(target.name).read_text(encoding="utf-8")

        self.assertIn('datetime="2026-08-27">27 августа 2026', result)
        self.assertIn('href="new.html"', result)
        self.assertIn("Новый материал", result)
        for marker in ('takprodam-verification', 'search-panel', 'KEEP SEARCH', 'KEEP FILTERS'):
            self.assertIn(marker, result)
        self.assertNotIn("OLD", result)

    def test_publication_pipeline_uses_preserving_refresh(self):
        source = (ROOT / "scripts" / "publish-article.py").read_text(encoding="utf-8")
        self.assertIn('scripts/refresh-homepage-latest.py', source)
        self.assertNotIn('scripts/build-homepage.py', source)


if __name__ == "__main__":
    unittest.main()
