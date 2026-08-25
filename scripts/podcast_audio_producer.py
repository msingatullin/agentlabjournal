#!/usr/bin/env python3
"""Generate and download audio from an approved podcast production package."""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

from podcast_contract import read_json, write_json

NOTEBOOKLM = "/root/scripts/notebooklm-via-gcp"
DEFAULT_NOTEBOOK = "3a91cab6-c483-4a8c-aadf-24afb78d8d8a"
EDGE_TTS = "/root/.venvs/notebooklm/bin/edge-tts"


def run(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-4000:])
    return result.stdout.strip()


def wait_for_artifact(notebook: str, artifact_id: str, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        payload = json.loads(run([NOTEBOOKLM, "artifact", "list", "--notebook", notebook, "--json"]))
        artifact = next((item for item in payload.get("artifacts", []) if item.get("id") == artifact_id), None)
        if artifact and artifact.get("status") == "completed":
            return
        if artifact and artifact.get("status") in {"failed", "cancelled", "canceled", "error"}:
            raise RuntimeError(f"Artifact terminal failure: {artifact_id}: {artifact.get('status')}")
        if artifact is None:
            raise RuntimeError(f"Artifact missing: {artifact_id}")
        time.sleep(30)
    raise TimeoutError(f"Artifact timeout: {artifact_id}")


def ensure_mp3(path: Path) -> None:
    probe = run(["ffprobe", "-v", "error", "-show_entries", "format=format_name", "-of", "default=nw=1:nk=1", str(path)])
    if probe == "mp3":
        return
    converted = path.with_suffix(".converted.mp3")
    subprocess.run(["ffmpeg", "-y", "-i", str(path), "-codec:a", "libmp3lame", "-b:a", "192k", str(converted)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    converted.replace(path)


def fallback_script(package: dict) -> str:
    lines = [
        package["intro_exact"],
        f"Артём: Сегодня {package['date']}. {package.get('news_window_label', 'Новости за последние 7 дней')}.",
    ]
    for index, item in enumerate(package["news"], 1):
        terms = ". ".join(item.get("qa_terms", []))
        lines.extend([
            f"Артём: Новость {index}. {item['title']}. Факт источника: {item['claim']}",
            f"Мира: Практическое значение: {item['why_it_matters']}",
            f"Артём: Контрольные формулировки. {terms}.",
        ])
    lines.extend([
        f"Мира: Рубрика {package['rubric']}. Тема: {package['daily_topic']}.",
        f"Артём: Практический вывод. {package['listener_takeaway']}",
        "Мира: Чек-лист. Первое: проверьте первичный источник. Второе: отделите факт от вывода. Третье: зафиксируйте практическое действие.",
        package["outro_exact"],
    ])
    return "\n\n".join(lines)


def generate_edge_tts(package: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agentlab-podcast-") as directory:
        temp_root = Path(directory)
        parts = []
        # Synthesize contract blocks separately. A single long edge-tts request
        # occasionally swallowed the first two checklist items and weakened the
        # brand/URL boundaries, which the transcript gate correctly rejected.
        for index, block in enumerate(fallback_script(package).split("\n\n")):
            part = temp_root / f"part-{index:02d}.mp3"
            subprocess.run([
                EDGE_TTS, "--voice", "ru-RU-SvetlanaNeural", "--rate=-5%",
                "--text", block, "--write-media", str(part),
            ], check=True, timeout=120)
            parts.append(part)
        concat = temp_root / "concat.txt"
        concat.write_text("".join(f"file '{part}'\n" for part in parts), encoding="utf-8")
        temporary = temp_root / "fallback.mp3"
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
            "-codec:a", "libmp3lame", "-b:a", "192k", str(temporary),
        ], check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        temporary.replace(output)
    ensure_mp3(output)
    if output.stat().st_size < 100_000:
        raise RuntimeError("Fallback audio is suspiciously small")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--notebook", default=DEFAULT_NOTEBOOK)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    package = read_json(args.package)
    if package.get("editorial_gate", {}).get("status") != "passed" or not package.get("production_prompt"):
        raise ValueError("EDITORIAL_GATE: BLOCKED")
    command = [NOTEBOOKLM, "generate", "audio", package["production_prompt"], "--notebook", args.notebook]
    for item in package["news"]:
        command.extend(["--source", item["source_id"]])
    command.extend(["--format", "deep-dive", "--length", "default", "--language", "ru", "--retry", "2", "--json"])
    try:
        payload = json.loads(run(command))
    except Exception as error:
        print(f"NOTEBOOKLM_AUDIO_UNAVAILABLE: using edge-tts fallback: {str(error)[-500:]}")
        generate_edge_tts(package, args.output)
        write_json(args.state, {
            "status": "audio_ready", "provider": "edge_tts_fallback",
            "package": str(args.package), "audio": str(args.output),
            "bytes": args.output.stat().st_size,
        })
        print(args.output)
        return 0
    artifact_id = payload.get("task_id") or payload.get("artifact_id") or payload.get("id")
    if not artifact_id:
        raise RuntimeError(f"No artifact id: {payload}")
    state = {"status": "generating", "artifact_id": artifact_id, "package": str(args.package)}
    write_json(args.state, state)
    wait_for_artifact(args.notebook, artifact_id, args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([NOTEBOOKLM, "download", "audio", str(args.output), "--notebook", args.notebook, "--artifact", artifact_id, "--force"], check=True)
    ensure_mp3(args.output)
    if args.output.stat().st_size < 100_000:
        raise RuntimeError("Audio is suspiciously small")
    state.update({"status": "audio_ready", "audio": str(args.output), "bytes": args.output.stat().st_size})
    write_json(args.state, state)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
