#!/usr/bin/env python3
"""Run the daily NotebookLM podcast generation after the editorial plan."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

ROOT = Path('/root')
PROJECT = Path('/root/agentlabjournal')
NOTEBOOK = 'fb0f2035-2378-47c1-9add-e7f27b223d56'
NOTEBOOKLM = '/root/.venvs/notebooklm/bin/notebooklm'


def run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default=dt.date.today().isoformat())
    parser.add_argument('--notebook', default=NOTEBOOK)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    plan_script = PROJECT / 'scripts' / 'daily-podcast-plan.py'
    subprocess.run(['/usr/bin/python3', str(plan_script), '--date', args.date, '--notebook', args.notebook], check=True)
    plan_path = ROOT / 'wiki/system' / f'daily-podcast-plan-{args.date}.json'
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    selection = plan['selection']
    prompt = (
        f"Создай русский выпуск Agent Lab Journal Podcast за {args.date}. "
        "Используй только проверенные факты и источники из текущего блокнота. "
        "Тема дня: " + str(selection.get('daily_topic') or '') + ". "
        "Сделай практичный выпуск для предпринимателей и разработчиков: новости, контекст, "
        "что проверить или применить. Не выдумывай факты, цифры и ссылки."
    )
    record = {
        'date': args.date,
        'notebook': args.notebook,
        'plan': str(plan_path),
        'status': 'planned',
        'started_at': dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    if args.dry_run:
        record['prompt'] = prompt
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0

    generated = run([
        NOTEBOOKLM, 'generate', 'audio', prompt,
        '--notebook', args.notebook,
        '--format', 'deep-dive', '--length', 'default', '--language', 'ru',
        '--wait', '--timeout', '1800', '--retry', '2', '--json',
    ])
    payload = json.loads(generated)
    artifact = payload.get('artifact') or payload
    artifact_id = artifact.get('id') or payload.get('artifact_id')
    if not artifact_id:
        raise RuntimeError(f'NotebookLM returned no artifact id: {payload}')

    output_dir = PROJECT / 'podcasts' / 'pending'
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f'agent-lab-journal-ru-{args.date}.mp3'
    subprocess.run([
        NOTEBOOKLM, 'download', 'audio', str(output),
        '--notebook', args.notebook, '--artifact', artifact_id, '--force',
    ], check=True)
    if output.stat().st_size < 100_000:
        raise RuntimeError(f'Generated audio is suspiciously small: {output}')
    record.update({'status': 'audio_ready', 'artifact_id': artifact_id, 'audio': str(output), 'bytes': output.stat().st_size})
    title = str(selection.get('daily_topic') or f'AI в работе: выпуск {args.date}')
    summary = str(selection.get('listener_takeaway') or 'Ежедневный практический выпуск Agent Lab Journal Podcast о проверяемых применениях AI.')
    publish = subprocess.run([
        '/usr/bin/python3', str(PROJECT / 'scripts' / 'publish-daily-podcast.py'),
        '--date', args.date, '--audio', str(output), '--title', title, '--summary', summary,
    ], text=True, capture_output=True)
    if publish.returncode != 0:
        record.update({'status': 'audio_ready_publish_blocked', 'publish_error': publish.stderr[-2000:]})
        state = ROOT / 'wiki/system' / f'daily-podcast-run-{args.date}.json'
        state.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        raise RuntimeError(f'Audio ready but publication failed: {publish.stderr[-1000:]}')
    record.update({'status': 'published', 'publish_output': publish.stdout[-4000:]})
    state = ROOT / 'wiki/system' / f'daily-podcast-run-{args.date}.json'
    state.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
