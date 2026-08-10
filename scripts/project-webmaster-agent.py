#!/usr/bin/env python3
"""Project-bound Yandex.Webmaster recrawl worker."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from podcast_contract import read_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--registry", type=Path, default=Path("/root/agentlabjournal/seo-project-agents.json"))
    parser.add_argument("--seo-passport", type=Path, required=True)
    parser.add_argument("--url", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registry = read_json(args.registry)
    project = registry.get("projects", {}).get(args.project_key)
    if not project:
        raise RuntimeError(f"WEBMASTER_PROJECT_AGENT: BLOCKED: unknown project {args.project_key}")
    passport = read_json(args.seo_passport)
    if passport.get("project_key") != args.project_key or passport.get("seo_query_gate") != "OK":
        raise RuntimeError("WEBMASTER_PROJECT_AGENT: BLOCKED: invalid SEO handoff")
    host = project["canonical_host"]
    results = []
    for url in args.url:
        if urlparse(url).hostname != host:
            raise RuntimeError(f"WEBMASTER_PROJECT_AGENT: BLOCKED: host mismatch {url}")
        command = ["/usr/bin/python3", "/root/agentlabjournal/scripts/submit-yandex-recrawl.py", "--host", host, "--url", url]
        result = subprocess.run(command, text=True, capture_output=True)
        if result.returncode:
            results.append({"url": url, "status": "BLOCKED", "error": (result.stderr or result.stdout)[-2000:]})
            continue
        payload = json.loads(result.stdout)
        results.append(payload)
    accepted = all(item.get("status") == "accepted" for item in results)
    output = {
        "agent": project["agent_id"].replace("seo-agent", "webmaster-agent"),
        "project_key": args.project_key, "status": "OK" if accepted else "BLOCKED",
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(), "results": results,
    }
    write_json(args.output, output)
    print(args.output)
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
