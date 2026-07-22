#!/usr/bin/env python3
"""Build stable section catalogs from the article queue and existing HTML pages."""
import json
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://agentlabjournal.online/"
SECTION_SLUGS = {
    "Новости AI": "news",
    "Практика": "practice",
    "Компании и продукты": "companies",
    "Инструменты": "tools",
    "Эксперименты": "experiments",
    "Разборы ошибок": "errors",
    "Безопасность": "security",
    "AI и деньги": "money",
    "Мнения": "opinions",
}

topics = json.loads((ROOT / "article-topics.json").read_text())
by_slug = {item["slug"]: item for item in topics}
articles = []
for path in sorted(ROOT.glob("*.html")):
    if not (path.name.startswith("guide-") or path.name.startswith("article-") or path.name.endswith("-case.html")):
        continue
    slug = path.stem
    item = by_slug.get(slug, {})
    category = item.get("category", "Практика")
    if category not in SECTION_SLUGS:
        category = "Практика"
    text = path.read_text()
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S | re.I)
    title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else slug.replace("-", " ").title()
    summary = item.get("summary", "Материал Agent Lab Journal")
    articles.append({"slug": slug, "title": title, "summary": summary, "category": category})

for section, section_slug in SECTION_SLUGS.items():
    entries = [item for item in articles if item["category"] == section]
    cards = "\n".join(
        f'<li><a class="text-link" href="{escape(item["slug"])}.html">{escape(item["title"])}</a><p>{escape(item["summary"])}</p></li>'
        for item in entries
    ) or "<li>Материалы для этого раздела готовятся.</li>"
    page = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{escape(section)} Agent Lab Journal"><link rel="canonical" href="{BASE}section-{section_slug}.html"><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="service.css"><title>{escape(section)} | Agent Lab Journal</title></head><body><header class="site-header"><a class="brand" href="./"><span class="brand-mark">AL</span><span>Agent Lab Journal</span></a><nav><a href="./">Главная</a><a href="sections.html">Разделы</a><a href="glossary.html">Словарь</a></nav></header><main class="article"><p class="eyebrow">РАЗДЕЛ ЖУРНАЛА</p><h1>{escape(section)}</h1><p class="lead">Материалы с проверяемыми источниками, практическими выводами и понятным уровнем сложности.</p><ol>{cards}</ol><p class="back"><a class="text-link" href="sections.html">← Все разделы</a></p><section class="service-note"><b>Мы публикуем то, что работает у нас — и внедряем это же для вашего бизнеса.</b> <a href="contacts.html">Обсудить задачу →</a></section></main><footer><span>Agent Lab Journal</span><span><a href="privacy-ru.html">Конфиденциальность</a></span></footer><script src="metrika.js"></script></body></html>'''
    (ROOT / f"section-{section_slug}.html").write_text(page)

sitemap = ROOT / "sitemap.xml"
sitemap_text = sitemap.read_text()
for section_slug in SECTION_SLUGS.values():
    url = f"{BASE}section-{section_slug}.html"
    if url not in sitemap_text:
        sitemap_text = sitemap_text.replace("</urlset>", f"  <url><loc>{url}</loc><changefreq>daily</changefreq><priority>0.6</priority></url>\n</urlset>", 1)
sitemap.write_text(sitemap_text)

print(f"SECTION_CATALOGS: built {len(SECTION_SLUGS)} catalogs")
