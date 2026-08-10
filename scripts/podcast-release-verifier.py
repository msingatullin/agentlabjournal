#!/usr/bin/env python3
"""Final read-only verifier for the podcast release handoff."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path("/root/agentlabjournal")

def http(url: str) -> int:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "AgentLabPodcastVerifier/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--yandex-confirmed", action="store_true")
    args = parser.parse_args()
    root = ROOT
    audio = root / "podcasts/pending" / f"agent-lab-journal-ru-{args.date}.mp3"
    page = f"https://agentlabjournal.online/podcast-{args.date}-ru.html"
    audio_url = f"https://microsrv.online/podcasts/agent-lab-journal-ru-{args.date}.mp3"
    guid = f"agentlabjournal-ru-{args.date}"
    checks = {
        "mp3_exists": audio.is_file() and audio.stat().st_size > 100_000,
        "mp3_valid": False,
        "page_http_200": False,
        "audio_http_200": False,
        "rss_guid_present": False,
        "yandex_feed_ready": False,
        "yandex_catalog_verified": bool(args.yandex_confirmed),
    }
    errors = []
    try:
        checks["page_http_200"] = http(page) == 200
    except Exception as error:
        errors.append(f"page: {error}")
    try:
        checks["audio_http_200"] = http(audio_url) == 200
    except Exception as error:
        errors.append(f"audio: {error}")
    try:
        live_rss = urllib.request.urlopen("https://agentlabjournal.online/podcast-rss.xml", timeout=30).read()
        rss_root = ET.fromstring(live_rss)
        checks["rss_guid_present"] = any(item.findtext("guid") == guid for item in rss_root.findall("./channel/item"))
    except Exception as error:
        errors.append(f"rss: {error}")
    if checks["mp3_exists"]:
        result = subprocess.run(["ffprobe", "-v", "error", str(audio)], capture_output=True)
        checks["mp3_valid"] = result.returncode == 0
    yandex = root / "podcasts/state" / f"{args.date}-ru-yandex.json"
    if yandex.is_file():
        checks["yandex_feed_ready"] = json.loads(yandex.read_text(encoding="utf-8")).get("status") == "feed_ready"
    public_release_verified = all(checks[key] for key in ("mp3_exists", "mp3_valid", "page_http_200", "audio_http_200", "rss_guid_present"))
    if public_release_verified and checks["yandex_catalog_verified"]:
        status = "OK"
    elif public_release_verified:
        status = "[BLOCKED: Yandex indexing unconfirmed]"
    else:
        status = "FAIL"
    payload = {"agent": "podcast-release-verifier", "status": status, "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(), "checks": checks, "errors": errors, "public_release_verified": public_release_verified, "yandex_catalog_ingestion": "confirmed_by_owner" if args.yandex_confirmed else "not_confirmable_via_public_api", "yandex_manual_check": "confirmed" if args.yandex_confirmed else "pending_owner_review"}
    args.handoff.parent.mkdir(parents=True, exist_ok=True)
    args.handoff.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if public_release_verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
