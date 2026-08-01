#!/usr/bin/env python3
"""Build the curated RU homepage as an editorial ecosystem index."""
from __future__ import annotations

from datetime import datetime
from html import escape, unescape
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://agentlabjournal.online/"
CONFIG = ROOT / "homepage-editorial.json"
COVERS = ROOT / "homepage-covers.json"


def plain(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def match(text: str, pattern: str, default: str = "") -> str:
    found = re.search(pattern, text, re.I | re.S)
    return plain(found.group(1)) if found else default


def creation_dates() -> dict[str, datetime]:
    result = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=@@%aI", "--name-only", "--", "*.html"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    dates: dict[str, datetime] = {}
    current: datetime | None = None
    for line in result.stdout.splitlines():
        if line.startswith("@@"):
            current = datetime.fromisoformat(line[2:])
        elif current and line and "/" not in line and line.endswith(".html"):
            dates.setdefault(line, current)
    return dates


def topic_categories() -> dict[str, str]:
    categories: dict[str, str] = {}
    for filename in ("topic-backlog-500.json", "article-topics.json"):
        for row in json.loads((ROOT / filename).read_text(encoding="utf-8")):
            slug = row.get("slug")
            if slug:
                categories[slug] = row.get("category") or row.get("section") or "Практика"
    return categories


def articles() -> dict[str, dict]:
    dates = creation_dates()
    categories = topic_categories()
    items: dict[str, dict] = {}
    for path in ROOT.glob("*.html"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r'"@type"\s*:\s*"(?:Article|NewsArticle|BlogPosting)"', text):
            continue
        title = match(text, r"<h1[^>]*>(.*?)</h1>")
        if not title:
            continue
        summary = match(text, r'<p[^>]*class="[^"]*lead[^"]*"[^>]*>(.*?)</p>')
        if not summary:
            summary = match(text, r'<meta[^>]+name="description"[^>]+content="([^"]+)"')
        reading = match(text, r'<(?:div|p)[^>]*class="[^"]*reading-meta[^"]*"[^>]*>(.*?)</(?:div|p)>')
        created = dates.get(path.name, datetime.fromtimestamp(path.stat().st_mtime).astimezone())
        items[path.stem] = {
            "slug": path.stem,
            "path": path.name,
            "title": title,
            "summary": summary,
            "reading": reading,
            "created": created,
            "category": categories.get(path.stem, "Практика"),
        }
    return items


MONTHS = ("", "января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")


def date_ru(value: datetime) -> str:
    return f"{value.day} {MONTHS[value.month]} {value.year}"


def require(item_map: dict[str, dict], slug: str) -> dict:
    if slug not in item_map:
        raise SystemExit(f"HOMEPAGE_EDITORIAL: configured article missing: {slug}")
    return item_map[slug]


def figure(item: dict, covers: dict, *, priority: bool = False) -> str:
    row = covers.get(item["slug"])
    if not row:
        raise SystemExit(f"HOMEPAGE_EDITORIAL: cover metadata missing: {item['slug']}")
    path = ROOT / row["path"]
    if not path.exists():
        raise SystemExit(f"HOMEPAGE_EDITORIAL: cover file missing: {row['path']}")
    loading = ' fetchpriority="high"' if priority else ' loading="lazy" decoding="async"'
    return (
        f'<figure class="story-cover"><img src="{escape(row["path"])}" '
        f'alt="{escape(row["alt"])}" width="1280" height="720"{loading}></figure>'
    )


def story_meta(item: dict) -> str:
    bits = [item["category"], date_ru(item["created"])]
    if item["reading"]:
        minutes = re.search(r"\b\d+\s*(?:минут|мин)\w*", item["reading"], re.I)
        if minutes:
            bits.append(minutes.group(0))
    return " · ".join(bits)


def build() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    covers = json.loads(COVERS.read_text(encoding="utf-8"))
    item_map = articles()
    lead = require(item_map, config["lead"])
    choices = [require(item_map, slug) for slug in config["editors_choice"]]
    deep = [require(item_map, slug) for slug in config["deep_reads"]]
    excluded = {lead["slug"], *(row["slug"] for row in choices), *(row["slug"] for row in deep)}
    latest = sorted((row for row in item_map.values() if row["slug"] not in excluded), key=lambda row: row["created"], reverse=True)[:6]

    latest_html = "\n".join(
        f'''          <li><a href="{escape(row['path'])}"><time datetime="{row['created'].date().isoformat()}">{date_ru(row['created'])}</time><span>{escape(row['title'])}</span></a></li>'''
        for row in latest
    )
    choices_html = "\n".join(
        f'''        <article class="story-card">
          <a class="story-card__cover" href="{escape(row['path'])}" aria-label="Открыть: {escape(row['title'])}">{figure(row, covers)}</a>
          <p class="story-meta">{escape(story_meta(row))}</p>
          <h3><a href="{escape(row['path'])}">{escape(row['title'])}</a></h3>
          <p>{escape(row['summary'])}</p>
        </article>'''
        for row in choices
    )
    deep_html = "\n".join(
        f'''        <article class="deep-story">
          <a class="deep-story__cover" href="{escape(row['path'])}" aria-label="Открыть: {escape(row['title'])}">{figure(row, covers)}</a>
          <div><p class="story-meta">{escape(story_meta(row))}</p><h3><a href="{escape(row['path'])}">{escape(row['title'])}</a></h3><p>{escape(row['summary'])}</p><a class="editorial-link" href="{escape(row['path'])}">Читать материал →</a></div>
        </article>'''
        for row in deep
    )

    now = datetime.now().astimezone()
    page = f'''<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="description" content="Agent Lab Journal — практический журнал об AI-агентах, автоматизации, безопасности и проверяемых экспериментах.">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Agent Lab Journal — AI-агенты для реальной работы">
  <meta property="og:description" content="Эксперименты, инструкции и разборы ошибок без скрытых ограничений и красивых обещаний.">
  <meta property="og:url" content="{BASE}">
  <meta property="og:image" content="{BASE}{covers[lead['slug']]['social_path']}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="canonical" href="{BASE}">
  <link rel="alternate" hreflang="ru" href="{BASE}">
  <link rel="alternate" hreflang="en" href="{BASE}en/">
  <link rel="alternate" hreflang="zh-CN" href="{BASE}zh/">
  <link rel="stylesheet" href="style.css">
  <link rel="stylesheet" href="homepage.css">
  <title>Agent Lab Journal — практический журнал об AI-агентах</title>
  <script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebSite","name":"Agent Lab Journal","url":"{BASE}","inLanguage":"ru-RU"}}</script>
  <script src="metrika.js"></script>
</head>
<body class="home-page"><noscript><div><img src="https://mc.yandex.ru/watch/110942679" class="metrika-pixel" alt=""></div></noscript>
  <header class="masthead">
    <div class="issue-line"><time datetime="{now.date().isoformat()}">{date_ru(now)}</time><span>Практический журнал об AI-системах</span><a href="en/">EN</a></div>
    <div class="masthead__name"><a href="./" aria-label="Agent Lab Journal, главная">Agent Lab Journal</a></div>
    <nav class="masthead__nav" aria-label="Основная навигация">
      <a href="section-practice.html">Практика</a><a href="section-tools.html">Инструменты</a><a href="section-security.html">Безопасность</a><a href="section-experiments.html">Эксперименты</a><a href="section-money.html">AI и деньги</a><a href="podcasts.html">Подкасты</a>
    </nav>
    <details class="mobile-menu"><summary>Меню</summary><nav aria-label="Мобильная навигация"><a href="section-practice.html">Практика</a><a href="section-tools.html">Инструменты</a><a href="section-security.html">Безопасность</a><a href="sections.html">Все разделы</a><a href="podcasts.html">Подкасты</a><a href="en/">English</a></nav></details>
  </header>
  <main class="homepage">
    <section class="positioning" aria-labelledby="positioning-title">
      <p id="positioning-title">Проверяем AI-инструменты на реальных сценариях и показываем не только результат, но и границы метода.</p>
      <a class="editorial-link" href="guides.html">Все материалы →</a>
    </section>
    <section class="front-page" aria-label="Главное и последнее">
      <article class="lead-story">
        <a class="lead-story__cover" href="{escape(lead['path'])}" aria-label="Открыть главный материал: {escape(lead['title'])}">{figure(lead, covers, priority=True)}</a>
        <p class="story-meta">Главный материал · {escape(story_meta(lead))}</p>
        <h1><a href="{escape(lead['path'])}">{escape(lead['title'])}</a></h1>
        <p class="lead-story__summary">{escape(lead['summary'])}</p>
        <a class="editorial-link" href="{escape(lead['path'])}">Читать исследование →</a>
      </article>
      <aside class="latest-rail" aria-labelledby="latest-title"><div class="rail-heading"><h2 id="latest-title">Новое</h2><a href="guides.html">Все →</a></div><ol>{latest_html}</ol></aside>
    </section>
    <section class="editorial-section" aria-labelledby="choice-title">
      <header class="section-title"><p>Отобрано редакцией</p><h2 id="choice-title">С чего продолжить</h2></header>
      <div class="choice-grid">{choices_html}</div>
    </section>
    <section class="editorial-section" aria-labelledby="deep-title">
      <header class="section-title"><p>Методики</p><h2 id="deep-title">Разобраться глубже</h2></header>
      <div class="deep-list">{deep_html}</div>
    </section>
    <section class="section-index" aria-labelledby="sections-title"><header class="section-title"><p>Навигация</p><h2 id="sections-title">По задаче</h2></header><div class="section-index__links"><a href="section-practice.html"><span>Практика</span><small>Внедрение и повторяемые инструкции</small></a><a href="section-tools.html"><span>Инструменты</span><small>Тесты моделей, MCP и инфраструктуры</small></a><a href="section-security.html"><span>Безопасность</span><small>Права, данные и контроль действий</small></a><a href="section-experiments.html"><span>Эксперименты</span><small>Метрики, сравнения и ограничения</small></a></div></section>
    <section class="journal-cta"><div><strong>Нужен такой контур в вашем процессе?</strong><span>Проектируем AI-автоматизацию с проверками, журналом действий и понятными границами.</span></div><a href="lead-intake.html">Обсудить задачу →</a></section>
  </main>
  <footer class="editorial-footer"><div class="editorial-footer__name">Agent Lab Journal</div><p>Практические эксперименты · проверяемые выводы · Москва, 2026</p><nav aria-label="Служебные ссылки"><a href="contacts.html">Контакты</a><a href="privacy-ru.html">Конфиденциальность</a><a href="terms-ru.html">Условия</a></nav></footer>
  <script src="content-bridge.js?v=20260728"></script>
</body>
</html>'''
    (ROOT / "index.html").write_text(page, encoding="utf-8")
    print(f"HOMEPAGE_EDITORIAL: built lead=1 latest={len(latest)} choice={len(choices)} deep={len(deep)}")


if __name__ == "__main__":
    build()
