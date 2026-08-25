# Агент-аналитик

Собирает раз в неделю (или по запросу) состояние всех проектов, финансов, outreach и задач, и выдаёт короткий отчёт с метриками, красными флагами и топ-3 рекомендациями.

## Запуск

```bash
/usr/bin/python3 /root/agentlabjournal/scripts/analyst/analyze.py
```

Отчёт сохраняется в `/root/wiki/agents/analyst/reports/YYYY-MM-DD.md`.

## Источники

- Git-логи репозиториев в `/root` — активность по проектам.
- `/root/wiki/finance/finance-chief-snapshot.json` — балансы и cash gap.
- `/root/mmw/docs/fundraising/fundraising-crm.md` — outreach-метрики.
- `/root/wiki/tasks/index.md` — статусы задач.
- `/root/agentlabjournal/podcast-rss.xml` — дата последнего подкаста.

## Выход

- Распределение времени (git-активность).
- Деньги и конверсия.
- Красные флаги.
- Топ-3 рекомендации.
- Базовые метрики для отслеживания.

## TODO

- Добавить парсинг доходов/расходов из `ledger.jsonl`.
- Улучшить подсчёт задач по формату `index.md`.
- Добавить целевые KPI и сравнение с предыдущей неделей.
- Подключить Telegram-уведомление с кратким summary.
