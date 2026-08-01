#!/usr/bin/env python3
"""Generate an article draft with Codex, then pass it through publication checks."""
from argparse import ArgumentParser
from html import unescape
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
parser = ArgumentParser(description="Generate and register a practical Agent Lab Journal article")
parser.add_argument("--slug", required=True, help="HTML filename without .html")
parser.add_argument("--title", required=True)
parser.add_argument("--problem", required=True)
parser.add_argument("--level", choices=["с нуля", "средний", "продвинутый"], default="средний")
parser.add_argument("--minutes", type=int, default=8)
parser.add_argument("--result", required=True)
parser.add_argument("--summary", required=True)
parser.add_argument("--news", action="store_true")
parser.add_argument("--language", choices=["ru", "en"], default="ru")
args = parser.parse_args()

filename = f"{re.sub(r'[^a-z0-9-]+', '-', args.slug.lower()).strip('-')}.html"
target = ROOT / filename if args.language == "ru" else ROOT / "en" / filename
target.parent.mkdir(exist_ok=True)
if target.exists():
    raise SystemExit(f"Refusing to overwrite existing article: {filename}")

seo_gate = subprocess.run([
    sys.executable,
    str(ROOT / "scripts" / "seo-query-gate.py"),
    "--slug",
    target.stem,
    "--language",
    args.language,
], cwd=ROOT)
if seo_gate.returncode:
    raise SystemExit("Generation blocked: SEO query passport is missing or invalid")

query_map = json.loads((ROOT / "seo-query-map.json").read_text(encoding="utf-8"))
base_passport = query_map["articles"][target.stem]
if base_passport.get("language") == args.language:
    seo_passport = base_passport
else:
    seo_passport = {**base_passport, **base_passport["localizations"][args.language]}
seo_queries = [row["query"] for row in seo_passport["measurements"]]
seo_brief = "\n".join(
    f"- {row['frequency_class']}: {row['query']} ({row['frequency_value']})"
    for row in seo_passport["measurements"]
)
glossary_href = "../glossary.html" if args.language == "en" else "glossary.html"

prompt = f"""Create one complete {'English' if args.language == 'en' else 'Russian'} HTML article for Agent Lab Journal.
Topic: {args.title}
Real problem: {args.problem}
Level: {args.level}
Reading time: {args.minutes} minutes
Expected result: {args.result}
SEO primary query: {seo_passport['primary_query']}
Measured SEO queries (use each exact phrase naturally, without keyword stuffing):
{seo_brief}

Return ONLY one complete HTML document, with no Markdown fences and no explanation.
Use the existing site style: style.css and reading.css. Add description, canonical URL
https://agentlabjournal.online/{'en/' if args.language == 'en' else ''}{filename}, title, and an Article JSON-LD block with headline,
description, image, dateModified, author, publisher and mainEntityOfPage. Add Open Graph and Twitter
card metadata, reading-meta, a strong lead, a concrete
case, practical steps, commands or configuration where useful, verification, failure cases,
limitations, and a final link to guides.html and {glossary_href}. The first mention of each
special term must link to {glossary_href} using an existing or appropriate anchor. Do not
invent test results, credentials, customer facts, or external citations. The article must
be useful to a reader who wants to repeat the work."""

if args.language == "ru" and os.environ.get("AGENTLAB_BATCH_MODE") == "1":
    prompt = f"""Напиши практическую русскоязычную статью для Agent Lab Journal.
Тема: {args.title}
Проблема: {args.problem}
Уровень: {args.level}; чтение: до {min(args.minutes, 12)} минут; результат: {args.result}.
Основной SEO-запрос: {seo_passport['primary_query']}.
Измеренные запросы — используй каждую точную фразу естественно, без переспама:
{seo_brief}
Верни только полный HTML-документ без Markdown и пояснений. Используй style.css и reading.css.
Обязательно добавь title, description, canonical https://agentlabjournal.online/{filename}, Open Graph,
Twitter card, reading-meta и Article JSON-LD. Дай введение, воспроизводимые шаги, безопасные команды или
конфигурацию, проверку результата, типовые ошибки, ограничения и ссылки на guides.html и glossary.html.
Не выдумывай тесты, клиентов, секреты или внешние источники; отличай пример от факта. Первый специальный
термин свяжи с glossary.html. Верни только HTML."""

with tempfile.TemporaryDirectory() as tmp:
    output = Path(tmp) / "article.txt"
    result = subprocess.run([
        "codex", "exec", "-c", "model_reasoning_effort=low", "--ephemeral", "--sandbox", "read-only",
        "--skip-git-repo-check", "-C", str(ROOT), "-o", str(output), prompt,
    ], text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, end="")
        print(result.stderr, file=sys.stderr, end="")
        raise SystemExit(result.returncode)
    html = output.read_text().strip()

html = re.sub(r"^\s*```(?:html)?\s*|\s*```\s*$", "", html, flags=re.I)
if not re.match(r"\s*<!doctype html>", html, flags=re.I) or "reading-meta" not in html:
    raise SystemExit("Generated output is not a valid article document")

def normalized(value: str) -> str:
    return " ".join(re.findall(r"[a-zа-яё0-9]+", unescape(value).casefold()))

visible_text = normalized(re.sub(r"<[^>]+>", " ", html))
title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.I | re.S)
description_match = re.search(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', html, flags=re.I
)
h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.I | re.S)
seo_surface = normalized(
    " ".join(match.group(1) if match else "" for match in (title_match, description_match, h1_match))
)
primary = normalized(seo_passport["primary_query"])
if primary not in seo_surface:
    raise SystemExit("Generated output failed SEO use gate: primary query missing from title/description/H1")
missing_queries = [query for query in seo_queries if normalized(query) not in visible_text]
if missing_queries:
    raise SystemExit(f"Generated output failed SEO use gate: missing measured queries {missing_queries}")
target.write_text(html + "\n")

publish = [sys.executable, str(ROOT / "scripts/publish-article.py"), "--file", str(target.relative_to(ROOT)), "--summary", args.summary]
if args.news:
    publish.append("--news")
raise SystemExit(subprocess.run(publish, cwd=ROOT).returncode)
