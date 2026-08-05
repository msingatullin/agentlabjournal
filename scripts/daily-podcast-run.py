#!/usr/bin/env python3
"""Dispatcher for the gated daily podcast workflow."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import subprocess
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT = Path("/root/agentlabjournal")
SCRIPTS = PROJECT / "scripts"
PYTHON = "/usr/bin/python3"
WHISPER = "/root/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "/root/whisper.cpp/models/ggml-small.bin"


def run(command: list[str], stage: str) -> None:
    print(f"PODCAST_STAGE: {stage}", flush=True)
    subprocess.run(command, cwd=PROJECT, check=True)


def notify_failure(stage: str, error: Exception) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_OWNER_ID") or os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    message = (
        "Agent Lab Journal: выпуск подкаста заблокирован\n"
        f"Этап: {stage}\n"
        f"Причина: {str(error)[:1000]}"
    )
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode()
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage", data=payload
            ),
            timeout=15,
        ).read()
    except Exception as notify_error:
        print(f"PODCAST_NOTIFY_FAILED: {notify_error}", flush=True)


def already_published(date: str, production: Path, audio: Path, qa: Path) -> bool:
    if not all(path.is_file() for path in (production, audio, qa)):
        return False
    qa_data = json.loads(qa.read_text(encoding="utf-8"))
    qa_audio = Path(qa_data.get("audio", ""))
    if not qa_audio.is_absolute():
        qa_audio = PROJECT / qa_audio
    if qa_data.get("status") != "passed" or qa_audio.resolve() != audio.resolve():
        return False
    package = json.loads(production.read_text(encoding="utf-8"))
    root = ET.parse(PROJECT / "podcast-rss.xml").getroot()
    for item in root.findall("./channel/item"):
        guid = item.findtext("guid", default="")
        title = item.findtext("title", default="")
        if guid == f"agentlabjournal-ru-{date}" and title == package["daily_topic"]:
            print(f"PODCAST_ALREADY_PUBLISHED: {date}", flush=True)
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--replacement", action="store_true")
    args = parser.parse_args()
    base = PROJECT / "podcasts"
    candidate = args.candidate or base / "packages" / f"{args.date}-ru.candidate.json"
    verified = base / "packages" / f"{args.date}-ru.verified.json"
    production = base / "packages" / f"{args.date}-ru.production.json"
    audio = base / "pending" / f"agent-lab-journal-ru-{args.date}.mp3"
    transcript_base = base / "transcripts" / f"{args.date}-ru"
    transcript = Path(str(transcript_base) + ".txt")
    qa = base / "qa" / f"{args.date}-ru.json"
    producer_state = base / "state" / f"{args.date}-ru-producer.json"
    lock_path = base / "state" / "daily-podcast.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("PODCAST_ALREADY_RUNNING", flush=True)
            return 0
        if already_published(args.date, production, audio, qa):
            return 0
        stage = "Research Agent"
        try:
            if not candidate.is_file():
                run([PYTHON, str(SCRIPTS / "daily-podcast-plan.py"), "--date", args.date], stage)
            stage = "Fact Verification Agent"
            run([PYTHON, str(SCRIPTS / "podcast_fact_verifier.py"), "--input", str(candidate), "--output", str(verified)], stage)
            stage = "Episode Editor Agent"
            run([PYTHON, str(SCRIPTS / "podcast_episode_editor.py"), "--input", str(verified), "--output", str(production)], stage)
            stage = "Audio Producer Agent"
            run([PYTHON, str(SCRIPTS / "podcast_audio_producer.py"), "--package", str(production), "--output", str(audio), "--state", str(producer_state)], stage)
            stage = "Transcript Agent"
            transcript.parent.mkdir(parents=True, exist_ok=True)
            run([WHISPER, "-m", WHISPER_MODEL, "-f", str(audio), "-l", "ru", "-t", "4", "-otxt", "-of", str(transcript_base)], stage)
            stage = "Transcript QA Agent"
            run([PYTHON, str(SCRIPTS / "podcast_transcript_qa.py"), "--package", str(production), "--transcript", str(transcript), "--audio", str(audio), "--output", str(qa)], stage)
            stage = "Publisher Agent"
            package = json.loads(production.read_text(encoding="utf-8"))
            run([
                PYTHON, str(SCRIPTS / "publish-daily-podcast.py"), "--date", args.date,
                "--audio", str(audio), "--title", package["daily_topic"],
                "--summary", package["listener_takeaway"], "--qa-manifest", str(qa),
            ], stage)
        except Exception as error:
            notify_failure(stage, error)
            raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
