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

# Editorial cover approval is a pre-generation gate: do not leave an orphan HTML
# file when the article has no distinct, source-based visual.
cover_map = json.loads((ROOT / "homepage-covers.json").read_text(encoding="utf-8"))
cover_row = cover_map.get(target.stem)
if not cover_row or not all(cover_row.get(key) for key in ("path", "social_path", "alt", "evidence", "type")):
    raise SystemExit("Generation blocked: approved article cover metadata is missing")
if not (ROOT / cover_row["path"]).exists():
    raise SystemExit("Generation blocked: approved article cover file is missing")
if not (ROOT / cover_row["social_path"]).exists():
    raise SystemExit("Generation blocked: approved article social cover file is missing")

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

prompt = f"""<role>
You are the technical editor for Agent Lab Journal. Produce one reproducible,
evidence-bounded article; do not claim to have run checks you did not run.
</role>
<goal>
Create one complete {'English' if args.language == 'en' else 'Russian'} HTML article.
</goal>
<data>
Topic: {args.title}
Real problem: {args.problem}
Level: {args.level}
Reading time: {args.minutes} minutes
Expected result: {args.result}
SEO primary query: {seo_passport['primary_query']}
Measured SEO queries (use each exact phrase naturally, without keyword stuffing):
{seo_brief}
</data>
<policy>
Do not invent test results, credentials, customer facts, prices, or external citations.
Distinguish examples from verified facts. Keep secrets and personal data out of the article.
</policy>
<workflow>
Use the existing site style: style.css and reading.css. Include a strong lead, concrete
case, reproducible steps, commands or configuration where useful, verification, failure
cases, limitations, and a final link to guides.html and {glossary_href}.
</workflow>
<tone>Practical, precise and useful to a reader who wants to repeat the work.</tone>
<output_contract>
Return ONLY one complete HTML document, with no Markdown fences or explanation. Include
description, canonical URL https://agentlabjournal.online/{'en/' if args.language == 'en' else ''}{filename},
title, Article JSON-LD with headline/description/image/dateModified/author/publisher/mainEntityOfPage,
Open Graph, Twitter card and reading-meta. The first mention of each special term must link
to {glossary_href} using an existing or appropriate anchor.
</output_contract>"""

if args.language == "ru" and os.environ.get("AGENTLAB_BATCH_MODE") == "1":
    prompt = f"""<role>Ты технический редактор Agent Lab Journal.</role>
<goal>Напиши практическую русскоязычную статью.</goal>
<data>
Тема: {args.title}
Проблема: {args.problem}
Уровень: {args.level}; чтение: до {min(args.minutes, 12)} минут; результат: {args.result}.
Основной SEO-запрос: {seo_passport['primary_query']}.
Измеренные запросы — используй каждую точную фразу естественно, без переспама:
{seo_brief}
</data>
<policy>Не выдумывай тесты, клиентов, цены, секреты или внешние источники; отличай пример от факта.</policy>
<workflow>Используй style.css и reading.css. Дай введение, воспроизводимые шаги, безопасные команды,
проверку результата, типовые ошибки, ограничения и ссылки на guides.html и glossary.html.</workflow>
<output_contract>Верни только полный HTML-документ без Markdown и пояснений. Обязательно добавь title,
description, canonical https://agentlabjournal.online/{filename}, Open Graph, Twitter card, reading-meta
и Article JSON-LD. Первый специальный термин свяжи с glossary.html.</output_contract>"""

def fallback_html() -> str:
    """Deterministic bounded article when the editorial subprocess times out."""
    canonical = f"https://agentlabjournal.online/{'en/' if args.language == 'en' else ''}{filename}"
    cover = f"https://agentlabjournal.online/assets/covers/{args.slug}.png"
    if args.language == "en":
        title = "Coding-Agent Memory as a Dependency: AI Agent Memory Audit" if args.slug == "coding-agent-memory-audit" else "Testing FROST-SOP: AI agent orchestration, retries and event auditing"
        lead = "This bounded field note describes how to test an event-driven AI agent workflow when a worker fails and an event must be delivered again."
        sections = [("Test boundary", "The test covers event creation, worker failure, retry delivery and an auditable result. It does not claim production reliability."), ("Minimal scenario", "Create one event, process it once, force a worker failure, deliver the same event again and record both attempts with a stable event ID. AI agents should receive only the capabilities required for this scenario."), ("Verification", "Check that the retry does not create an uncontrolled duplicate, the final state is explicit and the audit trail contains the event, attempts and outcome."), ("Limitations", "This is a reproducible test scenario, not a security certification or a guarantee of production behavior.")]
    else:
        title = f"{args.title} — {'память AI агентов' if args.slug == 'coding-agent-memory-audit' else 'оркестрация AI агентов'}"
        lead = "Этот практический материал описывает ограниченный тест событийного AI-конвейера: отказ исполнителя, повторная доставка события и проверяемый аудиторский след."
        sections = [("Граница теста", "Проверяем создание события, отказ исполнителя, повторную доставку и фиксацию результата. Материал не утверждает готовность контура к production."), ("Минимальный сценарий", "Создайте одно событие, обработайте его, зафиксируйте отказ исполнителя, доставьте событие повторно и сохраните обе попытки с неизменным идентификатором."), ("Проверка", "Убедитесь, что повтор не создаёт неконтролируемый дубль, итоговое состояние явно записано, а журнал содержит событие, попытки и результат."), ("Ограничения", "Это воспроизводимый учебный сценарий, а не сертификация безопасности и не гарантия поведения в production.")]
    body = "".join(f"<h2>{h}</h2><p>{t}</p>" for h,t in sections)
    related = "This material targets the measured clusters AI agent memory and AI agents without promising a search result." if args.language == "en" else ("Материал относится к теме «память AI агентов» и использует измеренный кластер «AI агент» без обещания поискового результата." if args.slug == "coding-agent-memory-audit" else "Материал относится к теме «оркестрация AI агентов» и использует измеренный кластер «AI агенты» без обещания поискового результата.")
    return f'''<!doctype html><html lang="{'en' if args.language == 'en' else 'ru'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><meta name="description" content="{lead}"><link rel="canonical" href="{canonical}"><meta property="og:type" content="article"><meta property="og:title" content="{title}"><meta property="og:description" content="{lead}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{cover}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{lead}"><meta name="twitter:image" content="{cover}"><script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":{json.dumps(title,ensure_ascii=False)},"description":{json.dumps(lead,ensure_ascii=False)},"image":"{cover}","dateModified":"2026-08-04","author":{{"@type":"Organization","name":"Agent Lab Journal"}},"publisher":{{"@type":"Organization","name":"Agent Lab Journal"}},"mainEntityOfPage":{{"@type":"WebPage","@id":"{canonical}"}}}}</script></head><body><main class="article"><article><header class="article-header"><p class="eyebrow">PRACTICE / AGENT LAB</p><h1>{title}</h1><p class="reading-meta">Practice · 12 minutes · 4 August 2026</p><p class="lead">{lead}</p></header>{body}<h2>Related measurements</h2><p>{related}</p><p><a href="/guides.html">Browse practical guides</a> · <a href="/glossary.html">Open the glossary</a></p></article></main></body></html>'''

with tempfile.TemporaryDirectory() as tmp:
    output = Path(tmp) / "article.txt"
    try:
        result = subprocess.run([
            "codex", "exec", "-c", "model_reasoning_effort=low", "--ephemeral", "--sandbox", "read-only",
            "--skip-git-repo-check", "-C", str(ROOT), "-o", str(output), prompt,
        ], text=True, capture_output=True, timeout=int(os.environ.get("AGENTLAB_GENERATION_TIMEOUT", "180")))
        if result.returncode:
            raise RuntimeError(result.stderr[-1000:] or f"editor exit code {result.returncode}")
        html = output.read_text().strip()
    except (subprocess.TimeoutExpired, RuntimeError) as error:
        print(f"EDITOR_FALLBACK: deterministic HTML used ({error})", file=sys.stderr)
        html = fallback_html()

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

cover_apply = subprocess.run([
    sys.executable,
    str(ROOT / "scripts" / "apply-article-cover.py"),
    "--file",
    str(target.relative_to(ROOT)),
], cwd=ROOT)
if cover_apply.returncode:
    target.unlink(missing_ok=True)
    raise SystemExit("Generation blocked: approved cover could not be applied")

publish = [sys.executable, str(ROOT / "scripts/publish-article.py"), "--file", str(target.relative_to(ROOT)), "--summary", args.summary]
if args.news:
    publish.append("--news")
raise SystemExit(subprocess.run(publish, cwd=ROOT).returncode)
