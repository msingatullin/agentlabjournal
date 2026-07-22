#!/usr/bin/env python3
"""Generate an article draft with Codex, then pass it through publication checks."""
from argparse import ArgumentParser
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
parser = ArgumentParser(description="Generate and register a practical Agent Lab Journal article")
parser.add_argument("--slug", required=True, help="HTML filename without .html")
parser.add_argument("--title", required=True)
parser.add_argument("--problem", required=True)
parser.add_argument("--level", choices=["с нуля", "средний", "продвинутый"], default="средний")
parser.add_argument("--minutes", type=int, default=8)
parser.add_argument("--result", required=True)
parser.add_argument("--summary", required=True)
parser.add_argument("--news", action="store_true")
parser.add_argument("--language", choices=["ru", "en"], default="ru")
args = parser.parse_args()

filename = f"{re.sub(r'[^a-z0-9-]+', '-', args.slug.lower()).strip('-')}.html"
target = ROOT / filename if args.language == "ru" else ROOT / "en" / filename
target.parent.mkdir(exist_ok=True)
if target.exists():
    raise SystemExit(f"Refusing to overwrite existing article: {filename}")

prompt = f"""Create one complete {'English' if args.language == 'en' else 'Russian'} HTML article for Agent Lab Journal.
Topic: {args.title}
Real problem: {args.problem}
Level: {args.level}
Reading time: {args.minutes} minutes
Expected result: {args.result}

Return ONLY one complete HTML document, with no Markdown fences and no explanation.
Use the existing site style: style.css and reading.css. Add description, canonical URL
https://agentlabjournal.online/{'en/' if args.language == 'en' else ''}{filename}, title, and an Article JSON-LD block with headline,
description, author, publisher and mainEntityOfPage. Add reading-meta, a strong lead, a concrete
case, practical steps, commands or configuration where useful, verification, failure cases,
limitations, and a final link to guides.html and glossary.html. The first mention of each
special term must link to glossary.html using an existing or appropriate anchor. Do not
invent test results, credentials, customer facts, or external citations. The article must
be useful to a reader who wants to repeat the work."""

with tempfile.TemporaryDirectory() as tmp:
    output = Path(tmp) / "article.txt"
    result = subprocess.run([
        "codex", "exec", "--ephemeral", "--sandbox", "read-only",
        "--skip-git-repo-check", "-C", str(ROOT), "-o", str(output), prompt,
    ], text=True, capture_output=True)
    if result.returncode:
        print(result.stdout, end="")
        print(result.stderr, file=sys.stderr, end="")
        raise SystemExit(result.returncode)
    html = output.read_text().strip()

html = re.sub(r"^\s*```(?:html)?\s*|\s*```\s*$", "", html, flags=re.I)
if not re.match(r"\s*<!doctype html>", html, flags=re.I) or "reading-meta" not in html:
    raise SystemExit("Generated output is not a valid article document")
target.write_text(html + "\n")

publish = [sys.executable, str(ROOT / "scripts/publish-article.py"), "--file", str(target.relative_to(ROOT)), "--summary", args.summary]
if args.news:
    publish.append("--news")
raise SystemExit(subprocess.run(publish, cwd=ROOT).returncode)
