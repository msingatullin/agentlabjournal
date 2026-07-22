#!/usr/bin/env python3
"""Generate, validate, commit and push one queued article."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
queue_path = ROOT / "article-topics.json"
topics = json.loads(queue_path.read_text())

for topic in topics:
    if not (ROOT / f"{topic['slug']}.html").exists():
        break
else:
    print("ARTICLE_CYCLE: queue exhausted")
    raise SystemExit(0)

command = [sys.executable, str(ROOT / "scripts/generate-article.py")]
for key in ("slug", "title", "problem", "level", "minutes", "result", "summary"):
    command.extend([f"--{key}", str(topic[key])])

result = subprocess.run(command, cwd=ROOT)
if result.returncode:
    raise SystemExit(result.returncode)

subprocess.run(["git", "add", "."], cwd=ROOT, check=True)
subprocess.run(["git", "commit", "-m", f"Publish article: {topic['title']}"], cwd=ROOT, check=True)
subprocess.run(["git", "push"], cwd=ROOT, check=True)
print(f"ARTICLE_CYCLE: published {topic['slug']}")
