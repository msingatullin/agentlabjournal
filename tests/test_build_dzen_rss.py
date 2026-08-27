#!/usr/bin/env python3
import subprocess
import shutil
import tempfile
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build-dzen-rss.py"
YANDEX_NS = "http://news.yandex.ru"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
MEDIA_NS = "http://search.yahoo.com/mrss/"


def article(*, slug: str, published: str, body: str) -> str:
    return textwrap.dedent(
        f"""\
        <!doctype html>
        <html lang="ru"><head>
          <title>Тестовая статья — Agent Lab Journal</title>
          <meta name="description" content="Проверяемая аннотация статьи.">
          <meta property="article:published_time" content="{published}">
          <meta property="article:section" content="Практика">
          <meta property="og:image" content="https://agentlabjournal.online/assets/covers/{slug}.png">
          <link rel="canonical" href="https://agentlabjournal.online/{slug}.html">
        </head><body><main><article>
          <h1>Тестовая статья</h1>
          <a class="max-promo-block" href="https://example.com/ad">Рекламный блок</a>
          {body}
          <section class="related"><h2>Читайте также</h2><p>Не включать.</p></section>
        </article></main></body></html>
        """
    )


def test_builds_recent_full_text_feed_and_excludes_promotional_blocks() -> None:
    """Catches feeds that publish summaries, stale items, or embedded promotions."""
    with tempfile.TemporaryDirectory() as directory:
        site = Path(directory)
        (site / "recent.html").write_text(
            article(
                slug="recent",
                published="2026-08-25T12:30:00+03:00",
                body=(
                    '<p>Первый полный абзац.</p><h2>Методика</h2><p>Второй полный абзац.</p>'
                    '<p><a href="https://agentlabjournal.online/guides.html">Перейти на сайт</a></p>'
                    '<p><a href="javascript:alert(1)">Опасная ссылка</a></p>'
                ),
            ),
            encoding="utf-8",
        )
        (site / "old.html").write_text(
            article(slug="old", published="2026-08-01T09:00:00+03:00", body="<p>Старый материал.</p>"),
            encoding="utf-8",
        )
        output = site / "dzen-rss.xml"

        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--root",
                str(site),
                "--output",
                str(output),
                "--now",
                "2026-08-27T18:00:00+03:00",
            ],
            text=True,
            capture_output=True,
        )

        assert result.returncode == 0, result.stderr
        tree = ET.parse(output)
        channel = tree.getroot().find("channel")
        assert channel is not None
        assert channel.findtext("language") == "ru"
        items = channel.findall("item")
        assert len(items) == 1
        item = items[0]
        assert item.findtext("link") == "https://agentlabjournal.online/recent.html"
        assert item.findtext("pubDate") == "Tue, 25 Aug 2026 12:30:00 +0300"
        full_text = item.findtext(f"{{{YANDEX_NS}}}full-text") or ""
        encoded = item.findtext(f"{{{CONTENT_NS}}}encoded") or ""
        raw_feed = output.read_text(encoding="utf-8")
        thumbnail = item.find(f"{{{MEDIA_NS}}}thumbnail")
        enclosure = item.find("enclosure")
        assert "Первый полный абзац" in full_text
        assert "Второй полный абзац" in full_text
        assert "Рекламный блок" not in full_text
        assert "Читайте также" not in full_text
        assert encoded.startswith("<h1>Тестовая статья</h1>")
        assert encoded.count("<figure>") == 1
        assert '<img src="https://agentlabjournal.online/assets/covers/recent.png"' in encoded
        assert '<a href="https://agentlabjournal.online/guides.html">Перейти на сайт</a>' in encoded
        assert "javascript:" not in encoded
        assert "<h2>Методика</h2>" in encoded
        assert "<content:encoded><![CDATA[<h1>" in raw_feed
        assert thumbnail is not None
        assert thumbnail.attrib["url"] == "https://agentlabjournal.online/assets/covers/recent.png"
        assert enclosure is not None
        assert enclosure.attrib == {
            "url": "https://agentlabjournal.online/assets/covers/recent.png",
            "type": "image/png",
        }
        assert [node.text for node in item.findall("category")] == ["format-article", "index", "comment-all"]
        assert item.find("author") is None


def test_accepts_date_only_publication_metadata_as_moscow_time() -> None:
    """Catches crashes on real articles whose JSON-LD date has no time component."""
    with tempfile.TemporaryDirectory() as directory:
        site = Path(directory)
        source = article(slug="date-only", published="", body="<p>Полный текст материала.</p>")
        source = source.replace(
            '<meta property="article:published_time" content="">',
            '<script type="application/ld+json">{"@type":"Article","datePublished":"2026-08-25"}</script>',
        )
        (site / "date-only.html").write_text(source, encoding="utf-8")
        output = site / "dzen-rss.xml"

        result = subprocess.run(
            ["python3", str(SCRIPT), "--root", str(site), "--output", str(output), "--now", "2026-08-27T18:00:00+03:00"],
            text=True,
            capture_output=True,
        )

        assert result.returncode == 0, result.stderr
        item = ET.parse(output).getroot().find("./channel/item")
        assert item is not None
        assert item.findtext("pubDate") == "Tue, 25 Aug 2026 00:00:00 +0300"


def test_regular_rss_build_refreshes_dzen_feed() -> None:
    """Catches publication runs that update the regular RSS but leave Dzen stale."""
    with tempfile.TemporaryDirectory() as directory:
        site = Path(directory)
        scripts = site / "scripts"
        scripts.mkdir()
        shutil.copy2(ROOT / "scripts" / "build-rss.py", scripts / "build-rss.py")
        shutil.copy2(SCRIPT, scripts / SCRIPT.name)
        (site / ".dzen-rss-connected").write_text("confirmed\n", encoding="utf-8")
        (site / "recent.html").write_text(
            article(slug="recent", published="2026-08-25T12:30:00+03:00", body="<p>Полный текст.</p>"),
            encoding="utf-8",
        )

        result = subprocess.run(["python3", str(scripts / "build-rss.py")], text=True, capture_output=True)

        assert result.returncode == 0, result.stderr
        assert (site / "dzen-rss.xml").is_file()
        assert ET.parse(site / "dzen-rss.xml").getroot().find("./channel/item") is not None


def test_regular_build_waits_for_ten_items_before_first_dzen_feed() -> None:
    """Catches publication automation that exposes a first feed before Dzen's initial gate passes."""
    with tempfile.TemporaryDirectory() as directory:
        site = Path(directory)
        scripts = site / "scripts"
        scripts.mkdir()
        shutil.copy2(ROOT / "scripts" / "build-rss.py", scripts / "build-rss.py")
        shutil.copy2(SCRIPT, scripts / SCRIPT.name)
        for number in range(9):
            slug = f"recent-{number}"
            (site / f"{slug}.html").write_text(
                article(slug=slug, published="2026-08-26T12:00:00+03:00", body="<p>Полный текст.</p>"),
                encoding="utf-8",
            )

        result = subprocess.run(["python3", str(scripts / "build-rss.py")], text=True, capture_output=True)

        assert result.returncode == 0, result.stderr
        assert "DZEN_RSS: WAITING" in result.stdout
        assert not (site / "dzen-rss.xml").exists()


def test_excludes_materials_older_than_three_days() -> None:
    """Catches Dzen feeds that submit material outside the documented freshness window."""
    with tempfile.TemporaryDirectory() as directory:
        site = Path(directory)
        (site / "four-days-old.html").write_text(
            article(slug="four-days-old", published="2026-08-23T12:00:00+03:00", body="<p>Полный текст.</p>"),
            encoding="utf-8",
        )
        output = site / "dzen-rss.xml"
        result = subprocess.run(
            ["python3", str(SCRIPT), "--root", str(site), "--output", str(output), "--now", "2026-08-27T18:00:00+03:00"],
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr
        assert ET.parse(output).getroot().find("./channel/item") is None


def test_initial_feed_requires_ten_recent_materials() -> None:
    """Catches an initial Dzen submission that cannot pass the documented ten-item gate."""
    with tempfile.TemporaryDirectory() as directory:
        site = Path(directory)
        for number in range(9):
            slug = f"recent-{number}"
            (site / f"{slug}.html").write_text(
                article(slug=slug, published="2026-08-26T12:00:00+03:00", body="<p>Полный текст.</p>"),
                encoding="utf-8",
            )
        result = subprocess.run(
            ["python3", str(SCRIPT), "--root", str(site), "--output", str(site / "feed.xml"), "--now", "2026-08-27T18:00:00+03:00", "--initial"],
            text=True,
            capture_output=True,
        )
        assert result.returncode != 0
        assert "requires at least 10 recent items" in result.stderr


if __name__ == "__main__":
    test_builds_recent_full_text_feed_and_excludes_promotional_blocks()
    test_accepts_date_only_publication_metadata_as_moscow_time()
    test_regular_rss_build_refreshes_dzen_feed()
    test_regular_build_waits_for_ten_items_before_first_dzen_feed()
    test_excludes_materials_older_than_three_days()
    test_initial_feed_requires_ten_recent_materials()
    print("TEST_BUILD_DZEN_RSS: OK")
