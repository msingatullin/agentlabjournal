# Skill: Article To Distribution

## Goal

Из одной опубликованной статьи создать проверяемый контент-пак, не публикуя
его автоматически.

## Input

- опубликованный HTML-файл статьи;
- query passport;
- подтверждённые ссылки и факты статьи.

## Workflow

1. Извлечь title, description, lead, headings и canonical.
2. Сформировать отдельные черновики для Telegram, LinkedIn/X и короткого видео.
3. Добавить canonical URL с UTM только через утверждённый шаблон проекта.
4. Проверить, что в черновиках нет новых фактов, цен, обещаний или цитат.
5. Передать пакет на ручное подтверждение.

## Stop conditions

- нет canonical;
- статья не прошла publication gate;
- нет query passport или measured frequency;
- обнаружен внешний факт без source reference.

## Output

`out/distribution/<slug>.json` со статусом `draft`, без сетевой публикации.
