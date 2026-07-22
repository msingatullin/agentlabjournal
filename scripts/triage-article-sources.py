#!/usr/bin/env python3
"""Use Codex to turn source candidates into bounded article topics."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sources_path = ROOT / "article-source-candidates.json"
topics_path = ROOT / "article-topics.json"
sources = json.loads(sources_path.read_text())
topics = json.loads(topics_path.read_text())
pending = [x for x in sources if x.get("status") == "needs_review"][:8]
if not pending:
    print("ARTICLE_TRIAGE: no pending candidates")
    raise SystemExit(0)

prompt = """You are the editor of a practical AI journal. Review the candidate sources below.
Approve only sources that can support an original article with a concrete test, comparison,
or implementation. Reject marketing-only, duplicate, vague, or unverifiable items.
Return ONLY a JSON array. Each approved object must have: slug, title, problem, level
(one of: с нуля, средний, продвинутый), minutes (integer), result, summary, source_url,
category. Return [] when none qualify.

CANDIDATES:
""" + json.dumps(pending, ensure_ascii=False)

with tempfile.TemporaryDirectory() as tmp:
    output = Path(tmp) / "triage.json"
    run = subprocess.run(["codex", "exec", "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check", "-C", str(ROOT), "-o", str(output), prompt], capture_output=True, text=True, timeout=600)
    if run.returncode:
        print(run.stderr, file=sys.stderr)
        raise SystemExit(run.returncode)
    raw = output.read_text().strip()

try:
    approved = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.I))
except json.JSONDecodeError as exc:
    raise SystemExit(f"Invalid triage JSON: {exc}")

existing = {x.get("slug") for x in topics}
known_urls = {x.get("source_url") for x in topics}
added = 0
for item in approved:
    if not item.get("slug") or item["slug"] in existing or item.get("source_url") in known_urls:
        continue
    item["status"] = "approved"
    topics.append(item)
    existing.add(item["slug"])
    known_urls.add(item.get("source_url"))
    added += 1

approved_urls = {x.get("source_url") for x in approved}
for item in sources:
    if item.get("url") in approved_urls:
        item["status"] = "approved"
    elif item.get("status") == "needs_review" and item in pending:
        item["status"] = "rejected"

topics_path.write_text(json.dumps(topics, ensure_ascii=False, indent=2) + "\n")
sources_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"approved": added, "queue": len(topics)}, ensure_ascii=False))
