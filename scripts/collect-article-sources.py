#!/usr/bin/env python3
"""Collect bounded GitHub and YouTube candidates for editorial triage."""
import json
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "article-source-candidates.json"
QUERIES = [
    ("Практика", "AI agent production workflow automation"),
    ("Инструменты", "LLM agent MCP open source tool"),
    ("Безопасность", "LLM agent security prompt injection guardrails"),
    ("Эксперименты", "LLM agent evaluation benchmark observability"),
]

def github(query):
    params = urllib.parse.urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": 3})
    req = urllib.request.Request(f"https://api.github.com/search/repositories?{params}", headers={"User-Agent": "AgentLabJournal"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read())
    return [{"url": x["html_url"], "title": x["full_name"], "description": x.get("description") or "", "source": "GitHub"} for x in data.get("items", [])]

def youtube(query):
    run = subprocess.run(["yt-dlp", "--flat-playlist", "--dump-single-json", "--skip-download", f"ytsearch3:{query}"], capture_output=True, text=True, timeout=120)
    if run.returncode:
        return []
    data = json.loads(run.stdout)
    return [{"url": f"https://www.youtube.com/watch?v={x['id']}", "title": x.get("title") or x["id"], "description": x.get("description") or "", "source": "YouTube"} for x in data.get("entries", []) if x.get("id")]

old = {x["url"]: x for x in json.loads(OUT.read_text())}
for category, query in QUERIES:
    try:
        found = github(query) + youtube(query)
    except Exception:
        found = []
    for item in found:
        item["category"] = category
        item["discovered_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        item["status"] = old.get(item["url"], {}).get("status", "needs_review")
        old[item["url"]] = item

items = list(old.values())[-200:]
OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"candidates": len(items), "new_for_review": sum(x["status"] == "needs_review" for x in items)}, ensure_ascii=False))
