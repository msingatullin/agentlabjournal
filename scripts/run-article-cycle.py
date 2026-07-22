#!/usr/bin/env python3
"""Generate, validate, commit and push one queued article."""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def load_env(path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

def notify(topic):
    time.sleep(120)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chats = os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "").replace(";", ",").split(",")
    url = f"https://agentlabjournal.online/{topic['slug']}.html"
    text = f"Agent Lab Journal: опубликована новая статья\n\n{topic['title']}\n{url}"
    if not token or not any(chat.strip() for chat in chats):
        print("ARTICLE_CYCLE: Telegram notification skipped; credentials or chat IDs missing")
        return
    for chat in chats:
        chat = chat.strip()
        if not chat:
            continue
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        with urllib.request.urlopen(request, timeout=20):
            pass
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
notify(topic)
print(f"ARTICLE_CYCLE: published {topic['slug']}")
