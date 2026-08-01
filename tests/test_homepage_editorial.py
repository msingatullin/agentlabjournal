#!/usr/bin/env python3
"""Regression checks for the generated homepage and its editorial gate."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent

for script in ("build-editorial-covers.py", "build-homepage.py", "check-homepage-editorial.py"):
    run = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, text=True, capture_output=True)
    assert run.returncode == 0, run.stdout + run.stderr

page = (ROOT / "index.html").read_text(encoding="utf-8")
css = (ROOT / "homepage.css").read_text(encoding="utf-8")
assert '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">' in page
assert page.count('class="story-card"') == 3
assert page.count('class="deep-story"') == 2
assert 'grid-template-columns: minmax(0, 1.8fr) minmax(18rem, 0.8fr)' in css
assert 'grid-template-columns: repeat(4, minmax(0, 1fr))' in css
assert "width: 100vw" not in css
assert "overflow-x: hidden" not in css
assert "transition: all" not in css
print("TEST_HOMEPAGE_EDITORIAL: OK")
