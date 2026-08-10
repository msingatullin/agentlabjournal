#!/usr/bin/env python3
"""Shared deterministic contract for Agent Lab Journal podcast stages."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

HOSTS = ["Артём", "Мира"]
INTRO_EXACT = "С вами Артём и Мира, это Agent Lab Journal Podcast."
OUTRO_EXACT = (
    "AgentLab помогает компаниям создавать AI-агентов, автоматизировать процессы "
    "и подключать AI к рабочим инструментам. Подробности на agentlabjournal.online."
)
RUBRICS = [
    "Новости недели", "AI в работу", "Человек vs Машина", "Под капот",
    "AI в России", "Будущее рядом", "Вопрос слушателя",
]


def expected_rubric(date_value: str) -> str:
    return RUBRICS[dt.date.fromisoformat(date_value).weekday()]


def read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_episode_package(payload: dict) -> None:
    required = ("date", "language", "rubric", "hosts", "intro_exact", "news", "daily_topic", "outro_exact")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise ValueError(f"Episode package misses fields: {', '.join(missing)}")
    if payload["language"] != "ru":
        raise ValueError("Only the RU daily pipeline is enabled")
    if payload["rubric"] != expected_rubric(payload["date"]):
        raise ValueError(f"Wrong rubric for date: {payload['rubric']}")
    if payload["hosts"] != HOSTS or payload["intro_exact"] != INTRO_EXACT:
        raise ValueError("Host or intro contract mismatch")
    if payload["outro_exact"] != OUTRO_EXACT:
        raise ValueError("Outro contract mismatch")
    if not 2 <= len(payload["news"]) <= 3:
        raise ValueError("Exactly 2-3 verified news items are required")
    for item in payload["news"]:
        for key in ("title", "date", "source_id", "source_url", "claim", "evidence_terms"):
            if not item.get(key):
                raise ValueError(f"News item misses {key}: {item.get('title', '<untitled>')}")
        if item.get("verification_status") != "verified":
            raise ValueError(f"Unverified news item: {item['title']}")


def build_generation_prompt(payload: dict) -> str:
    validate_episode_package(payload)
    news = "\n".join(
        f"{index}. {item['title']} ({item['date']}). Факт: {item['claim']} "
        f"Практическое значение: {item['why_it_matters']} "
        f"Обязательные контрольные формулировки, каждую произнести дословно хотя бы один раз: "
        f"{'; '.join(item['qa_terms'])}."
        for index, item in enumerate(payload["news"], 1)
    )
    news_window_label = payload.get("news_window_label", "Новости за последние 24 часа")
    return f"""Создай русский выпуск подкаста строго по этому утверждённому сценарию.

ОБЯЗАТЕЛЬНЫЕ ОГРАНИЧЕНИЯ:
- Используй только выбранные источники и факты ниже. Не добавляй другие новости, источники, компании, законы, цифры или статистику.
- Первые слова выпуска должны быть дословно: «{payload['intro_exact']}»
- Ведущие: Артём — объясняет; Мира — проверяет факты и задаёт практические вопросы. Называй их по именам.
- После приветствия произнеси дату {payload['date']} и заголовок «{news_window_label}».
- Разбери ровно {len(payload['news'])} новости, перечисленные ниже.
- В блоке каждой новости дословно произнеси все её контрольные формулировки.
- Затем явно объяви рубрику «{payload['rubric']}» и разбери тему «{payload['daily_topic']}».
- Отделяй факт источника от вывода ведущих. Не превращай исследование компании в универсальную статистику.
- Заверши практическим чек-листом из трёх действий.
- Последние слова выпуска должны быть дословно: «{payload['outro_exact']}»

ПРОВЕРЕННЫЕ НОВОСТИ:
{news}

ПРАКТИЧЕСКИЙ ВЫВОД:
{payload['listener_takeaway']}
"""
