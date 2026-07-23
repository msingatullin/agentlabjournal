#!/usr/bin/env python3
"""Collect bounded GitHub and YouTube candidates for editorial triage."""
import json
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "article-source-candidates.json"
MAX_CANDIDATES = 200
MAX_RESULTS_PER_QUERY = 3
QUERIES = [
    ("Практика", "AI agent production workflow automation"),
    ("Инструменты", "LLM agent MCP open source tool"),
    ("Безопасность", "LLM agent security prompt injection guardrails"),
    ("Эксперименты", "LLM agent evaluation benchmark observability"),
]
FEEDS = ROOT / "article-source-feeds.json"

def github(query):
    params = urllib.parse.urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": 3})
    req = urllib.request.Request(f"https://api.github.com/search/repositories?{params}", headers={"User-Agent": "AgentLabJournal"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read())
    return [{"url": x["html_url"], "title": x["full_name"], "description": x.get("description") or "", "source": "GitHub"} for x in data.get("items", [])[:MAX_RESULTS_PER_QUERY]]

def youtube(query):
    run = subprocess.run(["yt-dlp", "--flat-playlist", "--dump-single-json", "--skip-download", f"ytsearch3:{query}"], capture_output=True, text=True, timeout=120)
    if run.returncode:
        return []
    data = json.loads(run.stdout)
    return [{"url": f"https://www.youtube.com/watch?v={x['id']}", "title": x.get("title") or x["id"], "description": x.get("description") or "", "source": "YouTube"} for x in data.get("entries", [])[:MAX_RESULTS_PER_QUERY] if x.get("id")]

def rss(feed):
    req = urllib.request.Request(feed["url"], headers={"User-Agent": "AgentLabJournal/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        root = ET.fromstring(response.read())
    items = []
    for item in root.findall(".//item")[:5]:
        link = item.findtext("link") or ""
        if not link:
            continue
        items.append({"url": link, "title": item.findtext("title") or link, "description": item.findtext("description") or "", "source": feed["name"], "category": feed["category"]})
    return items

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

for feed in json.loads(FEEDS.read_text()):
    try:
        found = rss(feed)
    except Exception:
        found = []
    for item in found:
        item["discovered_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        item["status"] = old.get(item["url"], {}).get("status", "needs_review")
        old[item["url"]] = item

items = list(old.values())[-MAX_CANDIDATES:]
OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"candidates": len(items), "new_for_review": sum(x["status"] == "needs_review" for x in items)}, ensure_ascii=False))
