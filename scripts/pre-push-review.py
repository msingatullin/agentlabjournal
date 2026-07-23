#!/usr/bin/env python3
"""Read-only publication review before a push; never edits files or calls APIs."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
checks = [
    ['git', 'diff', '--check'],
    [sys.executable, str(ROOT / 'scripts' / 'verify-article-pair.py'), '--slug', 'deco-studio-agent-observability-test'],
    [sys.executable, str(ROOT / 'scripts' / 'test-publication-channels.py')],
]
for command in checks:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        print(result.stdout + result.stderr, end='')
        raise SystemExit(result.returncode)
print('pre-push review: OK')
