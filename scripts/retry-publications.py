#!/usr/bin/env python3
"""Retry only failed external publications recorded by run-article-cycle.py."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "publication-status.json"
COMMANDS = {
    "dev": ["publish-to-dev.py", "--publish"],
    "hashnode": ["publish-to-hashnode.py"],
    "blogger": ["publish-to-blogger.py"],
}

if not STATUS.exists():
    print(json.dumps({"retried": 0, "message": "publication-status.json not found"}, ensure_ascii=False))
    raise SystemExit(0)

state = json.loads(STATUS.read_text())
retried = []
failed = []
for slug, item in state.items():
    for channel, channel_state in item.get("channels", {}).items():
        if channel_state.get("status") != "error" or channel not in COMMANDS:
            continue
        source = ROOT / "en" / f"{slug}.html"
        if not source.exists():
            failed.append({"slug": slug, "channel": channel, "error": "source article is missing"})
            continue
        command = [sys.executable, str(ROOT / "scripts" / COMMANDS[channel][0]), "--file", str(source.relative_to(ROOT))]
        command.extend(COMMANDS[channel][1:])
        try:
            subprocess.run(command, cwd=ROOT, check=True)
            channel_state.clear()
            channel_state.update({"status": "published", "recovered": True})
            retried.append({"slug": slug, "channel": channel, "status": "published"})
        except Exception as exc:
            channel_state.update({"status": "error", "error": str(exc)[:1000]})
            failed.append({"slug": slug, "channel": channel, "error": str(exc)[:1000]})

STATUS.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"retried": len(retried), "failed": len(failed), "results": retried, "errors": failed}, ensure_ascii=False))
