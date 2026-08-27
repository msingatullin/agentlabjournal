from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FigureParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.article_figures = []
        self._in_reading = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "article" and "reading" in attributes.get("class", "").split():
            self._in_reading = True
        if tag == "figure" and self._in_reading:
            self.article_figures.append(attributes)

    def handle_endtag(self, tag):
        if tag == "article":
            self._in_reading = False


class NewsArticleLayoutTest(unittest.TestCase):
    def test_lead_image_uses_bounded_article_cover_layout(self):
        parser = FigureParser()
        parser.feed((ROOT / "google-ai-mode-travel-booking.html").read_text(encoding="utf-8"))

        self.assertEqual(1, len(parser.article_figures))
        classes = parser.article_figures[0].get("class", "").split()
        self.assertIn("article-cover", classes)


if __name__ == "__main__":
    unittest.main()
