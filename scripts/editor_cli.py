"""One text-only call to the editor model: Claude Code first, Codex when Claude is unavailable.

Both CLIs run without tools: the prompt goes in, plain text comes out. Claude's login on the server can
expire (2026-11-01: "OAuth session expired"), so a failed or empty Claude answer is retried with Codex.
"""
import subprocess
import sys
import tempfile
from pathlib import Path


def _claude(prompt: str, cwd, timeout: int) -> str:
    result = subprocess.run(["claude", "-p", "--output-format", "text", "--no-session-persistence", "--tools", ""],
                            input=prompt, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    text = result.stdout.strip()
    if result.returncode or not text or text.startswith("Failed to authenticate"):
        raise RuntimeError((result.stderr or result.stdout)[-500:] or f"claude exit {result.returncode}")
    return text


def _codex(prompt: str, cwd, timeout: int) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "answer.txt"
        result = subprocess.run(["codex", "exec", "--skip-git-repo-check", "-s", "read-only", "-o", str(out), "-"],
                                input=prompt, cwd=tmp, text=True, capture_output=True, timeout=timeout)
        text = out.read_text().strip() if out.exists() else ""
    if result.returncode or not text:
        raise RuntimeError((result.stderr or result.stdout)[-500:] or f"codex exit {result.returncode}")
    return text


def run_editor(prompt: str, cwd, timeout: int) -> str:
    try:
        return _claude(prompt, cwd, timeout)
    except (subprocess.TimeoutExpired, RuntimeError, OSError) as error:
        print(f"EDITOR: Claude unavailable ({str(error)[:200]}); trying Codex", file=sys.stderr)
    return _codex(prompt, cwd, timeout + 300)
