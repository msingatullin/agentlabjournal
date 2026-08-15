#!/usr/bin/env python3
"""Offline checks for the publication channel contract; no network calls."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cycle = (ROOT / 'scripts' / 'run-article-cycle.py').read_text()
retry = (ROOT / 'scripts' / 'retry-publications.py').read_text()
for filename in ('publish-to-dev.py', 'publish-to-hashnode.py', 'publish-to-blogger.py'):
    assert (ROOT / 'scripts' / filename).exists(), f'missing {filename}'
    assert filename in cycle, f'{filename} is not in the main cycle'
    assert filename in retry, f'{filename} is not recoverable'
ast.parse(cycle)
ast.parse(retry)
assert 'channel_errors' in cycle
assert "status': 'error'" in cycle
assert '"status": "error"' in retry
assert 'agentlabjournal-dev.env' in retry
assert 'agentlabjournal-hashnode.env' in retry
assert 'agentlabjournal-blogger.env' in retry
assert 'capture_output=True' in cycle
assert 'no publication-ready topics' in cycle
assert 'dirty worktree; refusing automatic generation and commit' in cycle
assert '["git", "add", "."]' not in cycle
print('publication channel contract tests: OK')
