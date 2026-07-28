#!/usr/bin/env python3
"""Publish the separate 500-topic backlog on the canonical Russian site only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "topic-backlog-500.json"
LOG = ROOT / "night-publish-500-20260729.log"

while not BACKLOG.exists():
    time.sleep(30)

topics = json.loads(BACKLOG.read_text())
if len(topics) != 500:
    raise SystemExit(f"Expected 500 topics, found {len(topics)}")

LOG.write_text("ONE_OFF_SITE_ONLY_PUBLISH_500 2026-07-29\n")
for index, topic in enumerate(topics, 1):
    slug = topic["slug"]
    target = ROOT / f"{slug}.html"
    if target.exists():
        with LOG.open("a") as handle:
            handle.write(f"SKIP existing {slug}\n")
        continue
    command = [sys.executable, str(ROOT / "scripts/generate-article.py")]
    for key in ("slug", "title", "problem", "level", "minutes", "result", "summary"):
        command.extend([f"--{key}", str(topic[key])])
    with LOG.open("a") as handle:
        handle.write(f"[{index}/500] {slug}\n")
        handle.flush()
        result = subprocess.run(command, cwd=ROOT, env={**os.environ, "AGENTLAB_BATCH_MODE": "1"}, stdout=handle, stderr=subprocess.STDOUT)
    if result.returncode:
        with LOG.open("a") as handle:
            handle.write(f"FAILED exit={result.returncode}\n")
        raise SystemExit(result.returncode)

check = subprocess.run([sys.executable, str(ROOT / "scripts/check-publication.py")], cwd=ROOT)
if check.returncode:
    raise SystemExit(check.returncode)
subprocess.run(["git", "add", "."], cwd=ROOT, check=True)
subprocess.run(["git", "commit", "-m", "Publish site-only batch of 500 RU articles"], cwd=ROOT, check=True)
subprocess.run(["git", "push"], cwd=ROOT, check=True)
with LOG.open("a") as handle:
    handle.write("SITE_ONLY_BATCH_500_COMMITTED_AND_PUSHED\n")
print("SITE_ONLY_BATCH_500_COMMITTED_AND_PUSHED")
