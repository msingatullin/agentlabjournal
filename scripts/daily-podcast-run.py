#!/usr/bin/env python3
"""Dispatcher for the gated daily podcast workflow."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import subprocess
import uuid
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT = Path("/root/agentlabjournal")
SCRIPTS = PROJECT / "scripts"
PYTHON = "/usr/bin/python3"
WHISPER = "/root/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "/root/whisper.cpp/models/ggml-small.bin"
STATE_DIR = Path("/tmp/podcast-state")
HANDOFF_ROOT = Path("/tmp/handoffs")
HANDOFF_DIR: Path | None = None


def handoff(step: str, agent: str, status: str, payload: dict | None = None) -> None:
    if HANDOFF_DIR is None:
        return
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    data = {"step": step, "agent": agent, "status": status, "updated_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    if payload:
        data.update(payload)
    (HANDOFF_DIR / f"{step}-{agent}-output.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_state(stage: str, status: str, error: str = "") -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "current-stage").write_text(stage + "\n", encoding="utf-8")
    (STATE_DIR / "last-run-status").write_text(status + "\n", encoding="utf-8")
    if error:
        (STATE_DIR / "last-error").write_text(error[:4000] + "\n", encoding="utf-8")
    elif (STATE_DIR / "last-error").exists():
        (STATE_DIR / "last-error").unlink()


def run(command: list[str], stage: str, expected: list[Path] | None = None) -> None:
    print(f"PODCAST_STAGE: {stage}", flush=True)
    write_state(stage, "RUNNING")
    agent = stage.lower().replace(" agent", "").replace(" ", "-")
    step = {"Research Agent": "02", "Fact Verification Agent": "03", "Project SEO Agent": "04", "Episode Editor Agent": "05", "Audio Producer Agent": "06", "Transcript Agent": "07", "Transcript QA Agent": "08", "Publisher Agent": "09", "Project Webmaster Agent": "10", "Release Verifier Agent": "11"}.get(stage, "99")
    previous = {"02": "01-dispatcher-output.json", "03": "02-research-output.json",
                "04": "03-fact-verification-output.json", "05": "04-project-seo-output.json",
                "06": "05-episode-editor-output.json", "07": "06-audio-producer-output.json",
                "08": "07-transcript-output.json", "09": "08-transcript-qa-output.json",
                "10": "09-publisher-output.json", "11": "10-project-webmaster-output.json"}.get(step)
    worker = [PYTHON, str(SCRIPTS / "podcast-stage-worker.py"), "--stage", stage,
              "--step", step, "--agent", agent, "--handoff-dir", str(HANDOFF_DIR),
              "--previous", previous]
    for path in expected or []:
        worker.extend(["--expect", str(path)])
    worker.extend(["--", *command])
    try:
        subprocess.run(worker, cwd=PROJECT, check=True)
    except Exception as error:
        write_state(stage, "FAIL", str(error))
        raise
    write_state(stage, "OK")


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


def already_published(date: str, production: Path, audio: Path, qa: Path, seo_passport: Path) -> bool:
    if not all(path.is_file() for path in (production, audio, qa)):
        return False
    qa_data = json.loads(qa.read_text(encoding="utf-8"))
    qa_audio = Path(qa_data.get("audio", ""))
    if not qa_audio.is_absolute():
        qa_audio = PROJECT / qa_audio
    if qa_data.get("status") != "passed" or qa_audio.resolve() != audio.resolve():
        return False
    package = json.loads(production.read_text(encoding="utf-8"))
    seo = json.loads(seo_passport.read_text(encoding="utf-8")) if seo_passport.is_file() else {}
    expected_title = seo.get("recommended_title") or package["daily_topic"]
    root = ET.parse(PROJECT / "podcast-rss.xml").getroot()
    for item in root.findall("./channel/item"):
        guid = item.findtext("guid", default="")
        title = item.findtext("title", default="")
        if guid == f"agentlabjournal-ru-{date}" and title == expected_title:
            print(f"PODCAST_ALREADY_PUBLISHED: {date}", flush=True)
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--replacement", action="store_true")
    args = parser.parse_args()
    global HANDOFF_DIR
    run_id = uuid.uuid4().hex[:12]
    HANDOFF_DIR = HANDOFF_ROOT / f"podcast-{args.date}-{run_id}"
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    (HANDOFF_DIR / "00-input.json").write_text(json.dumps({"project": "agentlabjournal-podcast", "date": args.date, "requested_by": "owner", "status": "accepted", "run_id": run_id}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    handoff("01", "dispatcher", "OK", {"scope": "single podcast episode", "date": args.date})
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    reset = STATE_DIR / "reset"
    if reset.exists():
        reset.unlink()
        write_state("reset", "RESET")
    elif (STATE_DIR / "last-run-status").read_text(encoding="utf-8").strip() == "FAIL" if (STATE_DIR / "last-run-status").exists() else False:
        print("PODCAST_STATE_LOCKED: create /tmp/podcast-state/reset", flush=True)
        return 2
    base = PROJECT / "podcasts"
    candidate = args.candidate or base / "packages" / f"{args.date}-ru.candidate.json"
    verified = base / "packages" / f"{args.date}-ru.verified.json"
    production = base / "packages" / f"{args.date}-ru.production.json"
    audio = base / "pending" / f"agent-lab-journal-ru-{args.date}.mp3"
    transcript_base = base / "transcripts" / f"{args.date}-ru"
    transcript = Path(str(transcript_base) + ".txt")
    qa = base / "qa" / f"{args.date}-ru.json"
    producer_state = base / "state" / f"{args.date}-ru-producer.json"
    seo_passport = base / "seo" / f"{args.date}-ru-query-passport.json"
    webmaster_handoff = base / "state" / f"{args.date}-ru-webmaster.json"
    lock_path = base / "state" / "daily-podcast.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("PODCAST_ALREADY_RUNNING", flush=True)
            return 0
        if already_published(args.date, production, audio, qa, seo_passport):
            verifier = base / "state" / f"{args.date}-ru-release-verifier.json"
            verifier_data = json.loads(verifier.read_text(encoding="utf-8")) if verifier.is_file() else {}
            if verifier_data.get("status") == "OK":
                write_state("complete", "OK")
                return 0
            write_state("Release Verifier Agent", "RUNNING", verifier_data.get("status", "verification pending"))
            return 3
        stage = "Research Agent"
        try:
            run([PYTHON, str(SCRIPTS / "daily-podcast-plan.py"), "--date", args.date], stage, [candidate])
            stage = "Fact Verification Agent"
            run([PYTHON, str(SCRIPTS / "podcast_fact_verifier.py"), "--input", str(candidate), "--output", str(verified)], stage, [verified])
            stage = "Project SEO Agent"
            canonical = f"https://agentlabjournal.online/podcast-{args.date}-ru.html"
            run([PYTHON, str(SCRIPTS / "project-seo-agent.py"), "--package", str(verified),
                 "--project-key", "agentlabjournal", "--canonical", canonical, "--output", str(seo_passport)], stage, [seo_passport])
            stage = "Episode Editor Agent"
            run([PYTHON, str(SCRIPTS / "podcast_episode_editor.py"), "--input", str(verified), "--output", str(production)], stage, [production])
            stage = "Audio Producer Agent"
            run([PYTHON, str(SCRIPTS / "podcast_audio_producer.py"), "--package", str(production), "--output", str(audio), "--state", str(producer_state)], stage, [audio, producer_state])
            stage = "Transcript Agent"
            transcript.parent.mkdir(parents=True, exist_ok=True)
            run([WHISPER, "-m", WHISPER_MODEL, "-f", str(audio), "-l", "ru", "-t", "4", "-otxt", "-of", str(transcript_base)], stage, [transcript])
            stage = "Transcript QA Agent"
            run([PYTHON, str(SCRIPTS / "podcast_transcript_qa.py"), "--package", str(production), "--transcript", str(transcript), "--audio", str(audio), "--output", str(qa)], stage, [qa])
            stage = "Publisher Agent"
            package = json.loads(production.read_text(encoding="utf-8"))
            run([
                PYTHON, str(SCRIPTS / "publish-daily-podcast.py"), "--date", args.date,
                "--audio", str(audio), "--title", package["daily_topic"],
                "--summary", package["listener_takeaway"], "--qa-manifest", str(qa), "--seo-passport", str(seo_passport),
            ], stage, [PROJECT / f"podcast-{args.date}-ru.html", PROJECT / "podcast-rss.xml"])
            stage = "Project Webmaster Agent"
            run([PYTHON, str(SCRIPTS / "project-webmaster-agent.py"), "--project-key", "agentlabjournal",
                 "--seo-passport", str(seo_passport), "--url", canonical,
                 "--url", "https://agentlabjournal.online/podcast-rss.xml", "--output", str(webmaster_handoff)],
                stage, [webmaster_handoff])
            stage = "Release Verifier Agent"
            verifier = base / "state" / f"{args.date}-ru-release-verifier.json"
            run([PYTHON, str(SCRIPTS / "podcast-release-verifier.py"), "--date", args.date,
                 "--webmaster-handoff", str(webmaster_handoff), "--handoff", str(verifier)], stage, [verifier])
            verifier_data = json.loads(verifier.read_text(encoding="utf-8"))
            if verifier_data.get("status") != "OK":
                write_state(stage, "RUNNING", verifier_data.get("status", "verification pending"))
                return 3
        except Exception as error:
            write_state(stage, "FAIL", str(error))
            notify_failure(stage, error)
            raise
        write_state("complete", "OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
