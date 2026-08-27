import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "check-article-layout.py"


class ArticleLayoutGateTest(unittest.TestCase):
    def run_gate(self, markup: str):
        with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8") as page:
            page.write(markup)
            page.flush()
            return subprocess.run(
                [sys.executable, str(GATE), "--file", page.name],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

    def test_blocks_new_article_without_bounded_article_container(self):
        result = self.run_gate('<main><article class="reading"><p>Text</p></article></main>')
        self.assertNotEqual(0, result.returncode)
        self.assertIn("bounded article container", result.stdout)

    def test_accepts_new_article_with_bounded_article_container(self):
        result = self.run_gate('<main class="article"><article class="reading"><p>Text</p></article></main>')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_publish_pipeline_runs_layout_gate_for_target_article(self):
        source = (ROOT / "scripts" / "publish-article.py").read_text(encoding="utf-8")
        self.assertIn('"check-article-layout.py"', source)
        self.assertIn('"--file", str(article)', source)


if __name__ == "__main__":
    unittest.main()
