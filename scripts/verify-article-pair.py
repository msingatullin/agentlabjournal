#!/usr/bin/env python3
"""Verify one RU/EN article pair before commit or external publication."""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--slug', required=True)
args = parser.parse_args()
errors = []
for relative, language in ((f'{args.slug}.html', 'ru'), (f'en/{args.slug}.html', 'en')):
    path = ROOT / relative
    if not path.exists():
        errors.append(f'{relative}: file missing')
        continue
    text = path.read_text(encoding='utf-8')
    if f'<h1' not in text or not re.search(r'<h1[^>]*>\s*\S', text, re.I):
        errors.append(f'{relative}: h1 missing')
    expected = f'https://agentlabjournal.online/{relative}'
    if f'rel="canonical" href="{expected}"' not in text:
        errors.append(f'{relative}: canonical URL mismatch')
if errors:
    print('\n'.join(errors))
    raise SystemExit(1)
print(f'article pair verification: OK ({args.slug})')
