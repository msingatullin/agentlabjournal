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
sys.path.insert(0, '/root')
from hermes_graph_engine import GraphRun, content_graph
STATUS_PATH = ROOT / "publication-status.json"

def update_status(slug, patch):
    data = json.loads(STATUS_PATH.read_text()) if STATUS_PATH.exists() else {}
    item = data.setdefault(slug, {'slug': slug, 'canonical': {}, 'channels': {}})
    item.update({k: v for k, v in patch.items() if k != 'channels'})
    item.setdefault('channels', {}).update(patch.get('channels', {}))
    item['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

def load_env(path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))

load_env(Path('/root/.config/agentlabjournal-hashnode.env'))

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

unpublished = [topic for topic in topics if not (ROOT / f"{topic['slug']}.html").exists()]
if not unpublished:
    print("ARTICLE_CYCLE: queue exhausted")
    raise SystemExit(0)

topic = None
blocked = []
for candidate in unpublished:
    candidate_ready = True
    for language in ("ru", "en"):
        seo_gate = subprocess.run([
            sys.executable,
            str(ROOT / "scripts" / "seo-query-gate.py"),
            "--slug",
            candidate["slug"],
            "--language",
            language,
        ], cwd=ROOT, capture_output=True, text=True)
        if seo_gate.returncode:
            candidate_ready = False
            blocked.append(f"{candidate['slug']}:{language}")
            break
    if candidate_ready:
        topic = candidate
        break

if topic is None:
    print(f"ARTICLE_CYCLE: no publication-ready topics; awaiting_measurement={len(unpublished)}")
    print("ARTICLE_CYCLE: blocked sample=" + ",".join(blocked[:10]))
    raise SystemExit(0)

print(f"ARTICLE_CYCLE: selected ready topic {topic['slug']}")
if os.environ.get("AGENTLAB_PREFLIGHT_ONLY") == "1":
    print(f"ARTICLE_CYCLE: preflight OK ({topic['slug']})")
    raise SystemExit(0)

worktree = subprocess.run(
    ["git", "status", "--porcelain"],
    cwd=ROOT,
    capture_output=True,
    text=True,
    check=True,
)
if worktree.stdout.strip():
    notify_error("git worktree safety gate", "uncommitted files exist; automatic git add is blocked")
    raise SystemExit("ARTICLE_CYCLE: dirty worktree; refusing automatic generation and commit")

graph_result = GraphRun(content_graph(), 'source').execute({
    'source': topic.get('summary', topic['title']),
    'topic': topic['slug'],
    'language': 'ru',
})
if graph_result['status'] != 'awaiting_verification':
    notify_error('graph preflight', f"run {graph_result['run_id']} status {graph_result['status']}")
    raise SystemExit(1)

command = [sys.executable, str(ROOT / "scripts/generate-article.py")]
for key in ("slug", "title", "problem", "level", "minutes", "result", "summary"):
    command.extend([f"--{key}", str(topic[key])])

cycle_env = os.environ.copy()
cycle_env.setdefault("AGENTLAB_BATCH_MODE", "1")
cycle_env.setdefault("AGENTLAB_GENERATION_TIMEOUT", "45")
subprocess.run([
    sys.executable,
    str(ROOT / "scripts" / "refresh-homepage-editorial.py"),
    "--file",
    str(ROOT / "homepage-editorial.json"),
    "--slug",
    topic["slug"],
], cwd=ROOT, check=True)
result = subprocess.run(command, cwd=ROOT, env=cycle_env)
if result.returncode:
    notify_error("генерация или publication gate", f"exit code {result.returncode}")
    raise SystemExit(result.returncode)
cta = subprocess.run([sys.executable, str(ROOT / "scripts" / "normalize-article-ctas.py"), f"{topic['slug']}.html"], cwd=ROOT)
if cta.returncode:
    notify_error("CTA order gate", f"exit code {cta.returncode}")
    raise SystemExit(cta.returncode)

english_command = [sys.executable, str(ROOT / "scripts/generate-article.py")]
english_values = {
    "slug": topic["slug"],
    "title": topic["en_title"],
    "problem": topic["en_problem"],
    "level": topic["level"],
    "minutes": topic["minutes"],
    "result": topic["en_result"],
    "summary": topic["en_summary"],
}
for key, value in english_values.items():
    english_command.extend([f"--{key}", str(value)])
english_command.extend(["--language", "en"])
english_result = subprocess.run(english_command, cwd=ROOT, env=cycle_env)
if english_result.returncode:
    notify_error("английская версия статьи", f"exit code {english_result.returncode}")
    raise SystemExit(english_result.returncode)

verify = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'verify-article-pair.py'), '--slug', topic['slug']], cwd=ROOT)
if verify.returncode:
    notify_error('проверка пары RU/EN', f'exit code {verify.returncode}')
    raise SystemExit(verify.returncode)

try:
    review = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'pre-push-review.py')], cwd=ROOT)
    if review.returncode:
        raise RuntimeError(f'pre-push review exit code {review.returncode}')
    subprocess.run(["git", "add", "--update"], cwd=ROOT, check=True)
    subprocess.run(["git", "add", f"{topic['slug']}.html", f"en/{topic['slug']}.html"], cwd=ROOT, check=True)
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
canonical_url = f"https://agentlabjournal.online/{topic['slug']}.html"
recrawl = subprocess.run([
    sys.executable,
    str(ROOT / "scripts" / "submit-yandex-recrawl.py"),
    "--url",
    canonical_url,
], cwd=ROOT)
if recrawl.returncode:
    notify_error("Yandex.Webmaster recrawl", f"{canonical_url}: exit code {recrawl.returncode}")
    raise SystemExit(recrawl.returncode)
update_status(topic['slug'], {'canonical': {'status': 'published', 'url': f"https://agentlabjournal.online/{topic['slug']}.html"}})
channel_errors = []
def publish_with_retry(command, attempts=3):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            subprocess.run(command, cwd=ROOT, check=True)
            return
        except Exception as error:
            last_error = error
            if attempt < attempts:
                time.sleep(10 * attempt)
    raise last_error

for script, label in (("publish-to-dev.py", "публикация английской статьи в DEV API"), ("publish-to-hashnode.py", "публикация английской статьи в Hashnode API"), ("publish-to-blogger.py", "публикация английской статьи в Blogger API")):
    channel = script.removeprefix('publish-to-').removesuffix('.py')
    try:
        command = [sys.executable, str(ROOT / "scripts" / script), "--file", f"en/{topic['slug']}.html"]
        if script == "publish-to-dev.py": command.append("--publish")
        publish_with_retry(command)
        update_status(topic['slug'], {'channels': {channel: {'status': 'published'}}})
    except Exception as error:
        channel_errors.append(f"{label}: {str(error)[:500]}")
        update_status(topic['slug'], {'channels': {channel: {'status': 'error', 'error': str(error)[:1000]}}})

if channel_errors:
    notify_error("частичный сбой внешних публикаций", "\n".join(channel_errors))
notify(topic)
print(f"ARTICLE_CYCLE: canonical published {topic['slug']}; external_errors={len(channel_errors)}")
