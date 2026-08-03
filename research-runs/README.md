# AgentLab Research Workflow

This directory contains metadata-only checkpoints for bounded research runs.
The runner stores topic, phase status, notes, budgets and evidence references;
it does not store API keys, private session content or generated code.

Use:

```bash
python3 scripts/research-workflow.py init --run-id seo-audit-20260803 --topic "SEO audit"
python3 scripts/research-workflow.py status --run-id seo-audit-20260803
python3 scripts/research-workflow.py complete --run-id seo-audit-20260803 --phase discovery --evidence wiki/projects/agent-lab-journal.md
```

Phases are ordered: `discovery -> evidence -> experiment -> review -> delivery`.
Review requires evidence; delivery requires a passed review. A run is resumed
from its JSON checkpoint instead of being reconstructed from chat history.
