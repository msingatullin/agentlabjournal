#!/usr/bin/env python3
"""Build a separate backlog of article ideas; never changes the publication queue."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "topic-backlog-500.json"
EXISTING = json.loads((ROOT / "article-topics.json").read_text())
known = {item["slug"] for item in EXISTING}
known.update(p.stem for p in ROOT.glob("*.html"))

prompt = """Составь ровно 100 новых тем для качественных русскоязычных статей Agent Lab Journal.
Тематика: AI-агенты, LLM, автоматизация, безопасность, MCP, RAG, наблюдаемость,
тестирование, стоимость, локальные модели, интеграции и практический бизнес в РФ.
Каждая тема должна быть проверяемой, практической и пригодной для отдельной статьи,
без выдуманных кейсов, клиентов, цифр и обещаний. Не повторяй общеизвестные шаблонные темы.
Верни только JSON-массив объектов с полями:
slug (ASCII kebab-case), title (русский), problem (русский), level (средний или продвинутый),
minutes (6-12), result (русский), summary (русский), category (одна из: Новости AI, Практика,
Компании и продукты, Инструменты, Эксперименты, Разборы ошибок, Безопасность, AI и деньги, Мнения).
Не добавляй Markdown и пояснения."""

items: list[dict] = []
for batch in range(5):
    result = subprocess.run(
        ["codex", "exec", "-c", "model_reasoning_effort=low", "--ephemeral", "--sandbox", "read-only",
         "--skip-git-repo-check", "-C", str(ROOT), prompt],
        capture_output=True, text=True, check=True,
    )
    text = result.stdout.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    chunk = json.loads(text)
    if not isinstance(chunk, list) or len(chunk) != 100:
        raise ValueError(f"batch {batch + 1}: expected 100 objects")
    items.extend(chunk)

unique: list[dict] = []
seen = set(known)
for item in items:
    slug = str(item.get("slug", "")).strip()
    required = {"slug", "title", "problem", "level", "minutes", "result", "summary", "category"}
    if required - item.keys() or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        continue
    if slug in seen:
        continue
    item["minutes"] = max(6, min(12, int(item["minutes"])))
    unique.append(item)
    seen.add(slug)

if len(unique) < 500:
    raise ValueError(f"only {len(unique)} unique new topics")
OUT.write_text(json.dumps(unique[:500], ensure_ascii=False, indent=2) + "\n")
print(f"TOPIC_BACKLOG: wrote {len(unique[:500])} unique topics to {OUT.name}")
