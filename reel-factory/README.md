# Reel Factory

Контур для анализа транскрипций популярных роликов и подготовки оригинальных сценариев.

## Поток

1. Положить транскрипцию в `sources/` в формате `.txt`.
2. Запустить:

```bash
python3 scripts/analyze-reel-transcripts.py sources/example.txt \
  --article-url https://agentlabjournal.online/article-example.html \
  --output analyses/example.json
```

3. Передать `analysis` в генератор сценариев. Текст источника используется только для анализа структуры и не копируется в публикацию.

Результат содержит хук, обещание, доказательства, CTA, признаки продажи, длину, темп и ограничения для оригинального сценария.

## Генерация сценария

```bash
python3 scripts/generate-reel-script.py analyses/example.json \
  --topic "автоматизация контентной воронки" \
  --output scripts-out/example.json
```

Сценарий рассчитан на двух вымышленных персонажей, содержит тайминг, реплики, B-roll, субтитры, CTA и UTM-ссылку. Перед публикацией нужно проверить факты статьи и фактическую доступность ссылки.
