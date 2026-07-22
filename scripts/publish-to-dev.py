#!/usr/bin/env python3
"""Publish an English article directly to DEV via its API."""
from argparse import ArgumentParser
from html.parser import HTMLParser
from pathlib import Path
import json
import os
import re
import urllib.request
import time
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parent.parent

class Markdown(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1
        if self.skip:
            return
        if tag in ('h1', 'h2', 'h3'):
            self.out.append('\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'p':
            self.out.append('\n')
        elif tag == 'li':
            self.out.append('\n- ')
        elif tag == 'pre':
            self.out.append('\n```\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self.skip:
            self.skip -= 1
        if not self.skip and tag == 'pre':
            self.out.append('\n```\n')
    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)

parser = ArgumentParser()
parser.add_argument('--file', required=True)
parser.add_argument('--publish', action='store_true')
parser.add_argument('--update', action='store_true')
args = parser.parse_args()
key = os.environ.get('DEV_API_KEY', '').strip()
if not key:
    raise SystemExit('DEV_API_KEY is missing')
path = ROOT / args.file
registry_path = ROOT / "dev-published.json"
registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
if args.file in registry and not args.update:
    print(json.dumps(registry[args.file], ensure_ascii=False))
    raise SystemExit(0)
text = path.read_text()
title_match = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S | re.I)
if not title_match:
    raise SystemExit('Article title not found')
title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
description = re.search(r'<meta name="description" content="([^"]*)"', text, re.I)
parser_html = Markdown()
parser_html.feed(text)
body = re.sub(r'\n{3,}', '\n\n', ''.join(parser_html.out)).strip()
canonical = f'https://agentlabjournal.online/{args.file}'
body += f'\n\n---\n\n**Original article:** {canonical}\n'
payload = {'article': {'title': title, 'body_markdown': body, 'published': bool(args.publish or args.update), 'canonical_url': canonical, 'description': description.group(1) if description else title, 'tags': ['ai', 'automation', 'agents']}}
method = 'PUT' if args.update else 'POST'
endpoint = f"https://dev.to/api/articles/{registry[args.file]['id']}" if args.update else 'https://dev.to/api/articles'
request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers={'api-key': key, 'Content-Type': 'application/json', 'Accept': 'application/vnd.forem.api-v1+json', 'User-Agent': 'Mozilla/5.0'}, method=method)
for attempt in range(3):
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read())
        break
    except HTTPError as error:
        if error.code != 429 or attempt == 2:
            raise
        time.sleep(65)
record = {'id': result.get('id'), 'url': result.get('url'), 'published': result.get('published')}
registry[args.file] = record
registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(record, ensure_ascii=False))
