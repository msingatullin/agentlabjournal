#!/usr/bin/env python3
"""Validate publication-status.json without contacting external services."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
path = ROOT / 'publication-status.json'
allowed = {'published', 'error', 'pending', 'skipped'}
errors = []

if not path.exists():
    print(json.dumps({'ok': True, 'articles': 0, 'message': 'no publication state yet'}, ensure_ascii=False))
    raise SystemExit(0)

try:
    data = json.loads(path.read_text())
except json.JSONDecodeError as exc:
    print(json.dumps({'ok': False, 'errors': [f'invalid JSON: {exc}']}, ensure_ascii=False))
    raise SystemExit(1)

for slug, item in data.items():
    canonical = item.get('canonical', {})
    if canonical.get('status') == 'published' and not str(canonical.get('url', '')).startswith('https://'):
        errors.append(f'{slug}: published canonical URL is missing')
    if canonical.get('status') not in allowed:
        errors.append(f'{slug}: unknown canonical status')
    for channel, state in item.get('channels', {}).items():
        if state.get('status') not in allowed:
            errors.append(f'{slug}/{channel}: unknown channel status')
        if state.get('status') == 'error' and not state.get('error'):
            errors.append(f'{slug}/{channel}: error status has no reason')

result = {'ok': not errors, 'articles': len(data), 'errors': errors}
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(0 if not errors else 1)
