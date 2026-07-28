#!/usr/bin/env python3
"""One-off batch: generate 50 new RU articles for the canonical site only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPICS = ROOT / "article-topics.json"
LOG = ROOT / "night-batch-20260728.log"

EXTRA = [
    ("agent-memory-failure-modes", "Память AI-агента: пять причин, почему контекст теряется", "Контекст агента исчезает между запусками или загрязняется старыми данными", "диагностику памяти и устойчивый контекст", "средний"),
    ("agent-permissions-by-tools", "Как ограничить права инструментов AI-агента", "Агенту дают слишком широкий доступ к файлам, API и командам", "минимальные права и журнал разрешений", "средний"),
    ("agent-retry-idempotency", "Повторные попытки AI-агента без дублей и побочных эффектов", "Сбой сети заставляет агента повторно выполнять уже завершённое действие", "идемпотентные операции и безопасные retry", "продвинутый"),
    ("agent-approval-workflow", "Контур подтверждения для опасных действий AI-агента", "Автоматизация должна останавливаться перед удалением, оплатой или публикацией", "очередь подтверждений и журнал решений", "средний"),
    ("agent-cost-budget-alerts", "Бюджеты и лимиты расходов для AI-агента", "Стоимость запросов растёт незаметно из-за длинного контекста и повторов", "лимиты, алерты и разбор стоимости", "средний"),
    ("agent-observability-minimum", "Минимальная наблюдаемость AI-агента без тяжёлой платформы", "Невозможно понять, где агент ошибся и сколько стоил запуск", "корреляционный ID, события и метрики", "средний"),
    ("agent-data-retention", "Как хранить данные AI-агента и не раздувать диск", "Логи, вложения и временные файлы постепенно заполняют сервер", "политику хранения, очистку и контроль места", "средний"),
    ("agent-telegram-security", "Безопасный Telegram-бот для бизнес-агента", "Бот принимает команды без проверки пользователя и контекста", "allowlist, подтверждения и безопасные ответы", "средний"),
    ("agent-webhook-reliability", "Надёжные webhook для AI-агента", "Входящие события теряются при таймаутах и повторной доставке", "приём событий, дедупликацию и повторную обработку", "продвинутый"),
    ("agent-queue-backpressure", "Очередь задач AI-агента: как пережить всплеск нагрузки", "Одновременные задания забивают память и замедляют обработку", "ограничение параллельности и backpressure", "продвинутый"),
    ("agent-file-upload-safety", "Безопасная обработка файлов, которые получает AI-агент", "Вложения могут быть слишком большими, вредоносными или неподдерживаемыми", "проверку типа, размера и изоляцию обработки", "средний"),
    ("agent-prompt-injection-checklist", "Чек-лист защиты агента от prompt injection", "Инструкции из документов и веб-страниц могут изменить поведение агента", "разделение данных и управляющих инструкций", "средний"),
    ("agent-source-grounding", "Как агент должен отличать факт от предположения", "Модель уверенно отвечает, даже когда в источниках нет подтверждения", "цитаты, происхождение данных и отказ от догадок", "средний"),
    ("agent-human-handoff", "Передача задачи от AI-агента человеку без потери контекста", "Сотрудник получает только ошибку, но не видит историю действий агента", "карточку передачи, причины и следующие шаги", "средний"),
    ("agent-slo-practical", "SLO для AI-агента: какие показатели действительно нужны", "Команда измеряет только доступность сервера и не видит качество результата", "доступность, задержку, качество и стоимость", "продвинутый"),
    ("agent-regression-dataset", "Регрессионный набор тестов для AI-агента", "После изменения промпта старые сценарии начинают работать хуже", "набор сценариев, эталоны и автоматическую проверку", "продвинутый"),
    ("agent-structured-output", "Структурированный вывод AI-агента вместо хрупкого текста", "Следующий этап не может надёжно разобрать свободный ответ модели", "схему данных, валидацию и обработку ошибок", "средний"),
    ("agent-api-timeouts", "Таймауты внешних API в цепочке AI-агента", "Один медленный сервис блокирует весь сценарий обработки", "таймауты, fallback и информативные статусы", "средний"),
    ("agent-secret-management", "Где хранить ключи и токены AI-агента", "Секреты попадают в код, логи или переписку", "переменные окружения, права и ротацию ключей", "средний"),
    ("agent-release-checklist", "Чек-лист выпуска AI-агента в production", "Рабочий прототип запускают без проверок отката и контроля доступа", "проверки перед релизом и план отката", "средний"),
    ("agent-failure-notifications", "Как правильно сообщать о сбоях AI-агента", "Владелец получает техническую ошибку без причины и следующего действия", "понятное уведомление, корреляцию и повторную диагностику", "средний"),
    ("agent-multi-tenant-isolation", "Изоляция данных клиентов в многопользовательском агенте", "Контекст одного клиента может попасть в ответ другому", "границы tenant, фильтры и тесты изоляции", "продвинутый"),
    ("agent-search-quality", "Как проверить качество поиска по базе знаний агента", "Агент получает нерелевантные фрагменты и формирует неверный ответ", "набор запросов, recall и ручную проверку", "продвинутый"),
]


def topic_from_extra(row: tuple[str, str, str, str, str]) -> dict:
    slug, title, problem, result, level = row
    return {"slug": slug, "title": title, "problem": problem, "level": level,
            "minutes": 8, "result": result, "summary": title}


def main() -> int:
    topics = json.loads(TOPICS.read_text())
    existing = {p.stem for p in ROOT.glob("*.html")}
    missing = [item for item in topics if item["slug"] not in existing]
    missing.extend(topic_from_extra(row) for row in EXTRA)
    if len(missing) > 50:
        raise SystemExit(f"Expected at most 50 pending articles, found {len(missing)}")

    LOG.write_text("ONE_OFF_RU_BATCH 2026-07-28\n")
    for index, item in enumerate(missing, 1):
        command = [sys.executable, str(ROOT / "scripts/generate-article.py")]
        for key in ("slug", "title", "problem", "level", "minutes", "result", "summary"):
            value = min(int(item[key]), 12) if key == "minutes" else item[key]
            command.extend([f"--{key}", str(value)])
        with LOG.open("a") as handle:
            handle.write(f"[{index}/50] {item['slug']}\n")
            handle.flush()
            result = subprocess.run(command, cwd=ROOT, env={**os.environ, "AGENTLAB_BATCH_MODE": "1"}, stdout=handle, stderr=subprocess.STDOUT)
        if result.returncode:
            with LOG.open("a") as handle:
                handle.write(f"FAILED exit={result.returncode}\n")
            return result.returncode

    check = subprocess.run([sys.executable, str(ROOT / "scripts/check-publication.py")], cwd=ROOT)
    if check.returncode:
        return check.returncode
    subprocess.run(["git", "add", "."], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", "Publish one-off batch of 50 RU articles"], cwd=ROOT, check=True)
    subprocess.run(["git", "push"], cwd=ROOT, check=True)
    with LOG.open("a") as handle:
        handle.write("BATCH_COMMITTED_AND_PUSHED\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
