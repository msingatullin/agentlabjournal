#!/usr/bin/env python3
"""Translate one existing article into an English counterpart."""
from argparse import ArgumentParser
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
parser = ArgumentParser()
parser.add_argument("--source", required=True)
args = parser.parse_args()
source = ROOT / args.source
if not source.exists() or source.parent != ROOT:
    raise SystemExit("Source article must be an existing root HTML file")
target = ROOT / "en" / source.name
if target.exists():
    raise SystemExit(f"Refusing to overwrite existing translation: {target.name}")
prompt = f'''Translate this Agent Lab Journal HTML article into accurate natural English.
Preserve the HTML structure, code, URLs, facts, numbers, caveats, reading metadata and glossary links.
Translate visible Russian text only. Do not add claims, examples, test results or marketing promises.
Set lang="en", canonical URL to https://agentlabjournal.online/en/{source.name}, and translate title and meta description.
Return only one complete HTML document.

SOURCE HTML:
{source.read_text()}'''
with tempfile.TemporaryDirectory() as tmp:
    output = Path(tmp) / "translation.html"
    result = subprocess.run(["codex", "exec", "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check", "-C", str(ROOT), "-o", str(output), prompt], text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(result.stderr or result.stdout)
    translated = output.read_text().strip()
if not translated.startswith("<!doctype html>") or 'lang="en"' not in translated:
    raise SystemExit("Translation failed structural checks")
target.write_text(translated + "\n")
print(f"Translated: {source.name} -> en/{target.name}")
