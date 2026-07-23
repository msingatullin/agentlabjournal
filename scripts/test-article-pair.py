import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
result = subprocess.run([sys.executable, str(root / 'scripts' / 'verify-article-pair.py'), '--slug', 'deco-studio-agent-observability-test'], cwd=root, capture_output=True, text=True)
assert result.returncode == 0, result.stdout + result.stderr
print('article pair verification test: OK')
