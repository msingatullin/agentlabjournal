#!/usr/bin/env python3
"""Run the publication cycle from a clean, disposable checkout."""
from pathlib import Path
import subprocess
import tempfile


REMOTE = "git@github.com:msingatullin/agentlabjournal.git"


def run_isolated(base: Path, run=subprocess.run) -> int:
    checkout = base / "repo"
    # Full history: build-homepage.py dates articles via `git log --diff-filter=A`;
    # in a shallow clone every article gets one date and the «Новое» rail breaks.
    clone = run(["git", "clone", REMOTE, str(checkout)])
    if clone.returncode:
        return clone.returncode
    cycle = run(
        ["/usr/bin/python3", str(checkout / "scripts" / "run-article-cycle.py")],
        cwd=checkout,
    )
    return cycle.returncode


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="agentlab-article-cycle-") as directory:
        return run_isolated(Path(directory))


if __name__ == "__main__":
    raise SystemExit(main())
