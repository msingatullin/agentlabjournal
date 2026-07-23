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

def notify_error(stage, error):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chats = os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "").replace(";", ",").split(",")
    if not token:
        print(f"ARTICLE_CYCLE: error notification skipped ({stage})")
        return
    text = f"Agent Lab Journal: ошибка автоматического цикла\nЭтап: {stage}\nПричина: {str(error)[:1200]}"
    for chat in chats:
        if not chat.strip():
            continue
        data = urllib.parse.urlencode({"chat_id": chat.strip(), "text": text}).encode()
        request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        with urllib.request.urlopen(request, timeout=20):
            pass

def wait_until_public(topic, attempts=40, delay=15):
    """Do not distribute a canonical URL until GitHub Pages serves it."""
    url = f"https://agentlabjournal.online/{topic['slug']}.html"
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "AgentLabJournalPublicationGate/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                if response.status == 200:
                    print(f"PUBLIC_URL_GATE: OK ({url}, attempt {attempt})")
                    return
        except Exception:
            pass
        if attempt < attempts:
            time.sleep(delay)
    raise RuntimeError(f"canonical URL is not publicly available after {attempts * delay}s: {url}")
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
    notify_error("генерация или publication gate", f"exit code {result.returncode}")
    raise SystemExit(result.returncode)

english_command = command + ["--language", "en"]
english_result = subprocess.run(english_command, cwd=ROOT)
if english_result.returncode:
    notify_error("английская версия статьи", f"exit code {english_result.returncode}")
    raise SystemExit(english_result.returncode)

try:
    subprocess.run(["git", "add", "."], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", f"Publish article: {topic['title']}"], cwd=ROOT, check=True)
except Exception as error:
    notify_error("commit или push", error)
    raise
try:
    subprocess.run(["git", "push"], cwd=ROOT, check=True)
except Exception as error:
    notify_error("push статьи", error)
    raise
try:
    wait_until_public(topic)
except Exception as error:
    notify_error("проверка публичной ссылки", error)
    raise
for script, label in (("publish-to-dev.py", "публикация английской статьи в DEV API"), ("publish-to-hashnode.py", "публикация английской статьи в Hashnode API"), ("publish-to-blogger.py", "публикация английской статьи в Blogger API")):
    try:
        command = [sys.executable, str(ROOT / "scripts" / script), "--file", f"en/{topic['slug']}.html"]
        if script == "publish-to-dev.py": command.append("--publish")
        subprocess.run(command, cwd=ROOT, check=True)
    except Exception as error:
        notify_error(label, error)
        raise
notify(topic)
print(f"ARTICLE_CYCLE: published {topic['slug']}")
