"""Publish an English article to Blogger."""
from argparse import ArgumentParser
from pathlib import Path
import json, os, re, urllib.parse, urllib.request

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = Path(os.environ.get('BLOGGER_TOKEN_FILE', '/root/.config/blogger-token.json'))
BLOG_ID = os.environ.get('BLOGGER_BLOG_ID', '496084951039088012')

def access_token():
    token = json.loads(TOKEN_FILE.read_text())
    data = urllib.parse.urlencode({'client_id': token['client_id'], 'client_secret': token['client_secret'], 'refresh_token': token['refresh_token'], 'grant_type': 'refresh_token'}).encode()
    req = urllib.request.Request(token['token_uri'], data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read())['access_token']

parser = ArgumentParser(); parser.add_argument('--file', required=True); parser.add_argument('--update', action='store_true'); args = parser.parse_args()
path = ROOT / args.file; registry_path = ROOT / 'blogger-published.json'
registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
if args.file in registry and not args.update:
    print(json.dumps(registry[args.file], ensure_ascii=False)); raise SystemExit(0)
text = path.read_text(); title_match = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S | re.I)
if not title_match: raise SystemExit('Article title not found')
title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
body_match = re.search(r'<body[^>]*>(.*?)</body>', text, re.S | re.I)
if not body_match: raise SystemExit('Article body not found')
body = re.sub(r'<script\b.*?</script>', '', body_match.group(1), flags=re.S | re.I)
paragraphs = re.findall(r'<(?:p|h2|h3)\b[^>]*>.*?</(?:p|h2|h3)>', body, flags=re.S | re.I)
body = '\n'.join(paragraphs[:8])
canonical = f'https://agentlabjournal.online/{args.file}'
tracked = canonical + '?utm_source=blogger&utm_medium=referral&utm_campaign=agentlabjournal'
body += f'\n<p><strong>Полная версия:</strong> <a href="{tracked}">{tracked}</a></p>'
payload = json.dumps({'kind': 'blogger#post', 'title': title, 'content': body, 'labels': ['AI', 'Automation', 'Agents']}).encode()
method = 'PUT' if args.update else 'POST'
post_id = f"/{registry[args.file]['id']}" if args.update else ''
url = f'https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts{post_id}?isDraft=false'
req = urllib.request.Request(url, data=payload, headers={'Authorization': 'Bearer ' + access_token(), 'Content-Type': 'application/json'}, method=method)
with urllib.request.urlopen(req, timeout=60) as response: result = json.loads(response.read())
record = {k: result.get(k) for k in ('id', 'url', 'title')}; registry[args.file] = record
registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n'); print(json.dumps(record, ensure_ascii=False))
