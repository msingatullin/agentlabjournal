# AgentLab Research Workflow

This directory contains metadata-only checkpoints for bounded research runs.
The runner stores topic, phase status, notes, budgets and evidence references;
it does not store API keys, private session content or generated code.

Use:

```bash
python3 scripts/research-workflow.py init --run-id seo-audit-20260803 --topic "SEO audit" \
  --hypothesis "Измеримый аудит найдёт повторяемую проблему" \
  --method "Сравнение baseline и проверочного прогона" \
  --acceptance "Результат воспроизводится и имеет evidence"
python3 scripts/research-workflow.py status --run-id seo-audit-20260803
python3 scripts/research-workflow.py complete --run-id seo-audit-20260803 --phase discovery --evidence wiki/projects/agent-lab-journal.md
```

Phases are ordered: `discovery -> evidence -> experiment -> review -> delivery`.
Evidence, a hypothesis, a method and acceptance criteria are required before an
experiment. Review requires evidence; delivery requires a passed review. A run is resumed
from its JSON checkpoint instead of being reconstructed from chat history.

Перед delivery подготовьте JSON-отчёт по `report.schema.json` и runtime-артефакт:

```bash
python3 scripts/collect-runtime-evidence.py --run-id seo-audit-20260803 \
  --file /path/to/result.json --url https://example.com
python3 scripts/research-workflow.py complete --run-id seo-audit-20260803 \
  --phase delivery --report /path/to/report.json \
  --runtime-evidence research-runs/seo-audit-20260803/runtime-evidence.json
```

Delivery-gate проверяет обязательные поля, происхождение evidence и успешные
runtime-проверки. Оценка качества источников выполняется `score-evidence.py`;
оценка не заменяет доказательство и не повышает слабый источник до факта.
