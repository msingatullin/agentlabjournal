"""Publish an English article to Blogger."""
from argparse import ArgumentParser
from pathlib import Path
import json, os, re, time, urllib.parse, urllib.request
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tracking import tracked_url
TOKEN_FILE = Path(os.environ.get('BLOGGER_TOKEN_FILE', '/root/.config/blogger-token.json'))
BLOG_ID = os.environ.get('BLOGGER_BLOG_ID', '496084951039088012')

def access_token():
    token = json.loads(TOKEN_FILE.read_text())
    data = urllib.parse.urlencode({'client_id': token['client_id'], 'client_secret': token['client_secret'], 'refresh_token': token['refresh_token'], 'grant_type': 'refresh_token'}).encode()
    req = urllib.request.Request(token['token_uri'], data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read())['access_token']
    except HTTPError as error:
        detail = error.read().decode('utf-8', 'replace')
        try:
            parsed = json.loads(detail)
            detail = f"{parsed.get('error', 'unknown')}: {parsed.get('error_description', '')}".strip()
        except json.JSONDecodeError:
            detail = detail[-1000:]
        raise SystemExit(f'Blogger OAuth refresh HTTP {error.code}: {detail}')

parser = ArgumentParser(); parser.add_argument('--file', required=True); parser.add_argument('--update', action='store_true'); parser.add_argument('--delete', action='store_true'); parser.add_argument('--country', default=os.environ.get('AGENTLAB_COUNTRY', 'global')); parser.add_argument('--region', default=os.environ.get('AGENTLAB_REGION', 'all')); parser.add_argument('--language', default='en'); args = parser.parse_args()
path = ROOT / args.file; registry_path = ROOT / 'blogger-published.json'
registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
if args.delete:
    if args.file not in registry or not registry[args.file].get('id'):
        raise SystemExit('Blogger post is not present in the publication registry')
    post_id = registry[args.file]['id']
    url = f'https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/{post_id}'
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + access_token()}, method='DELETE')
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            response.read()
    except HTTPError as error:
        detail = error.read().decode('utf-8', 'replace')
        raise SystemExit(f'Blogger delete HTTP {error.code}: {detail[-1000:]}')
    registry[args.file]['deleted'] = True
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'id': post_id, 'deleted': True}, ensure_ascii=False))
    raise SystemExit(0)
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
letters = re.findall(r'[A-Za-z\u0400-\u04ff]', title + '\n' + body)
cyrillic = re.findall(r'[\u0400-\u04ff]', title + '\n' + body)
if args.language == 'en' and letters and len(cyrillic) / len(letters) > 0.05:
    raise SystemExit('English-only Blogger gate blocked publication: Cyrillic content detected')
canonical = f'https://agentlabjournal.online/{args.file}'
tracked = tracked_url(canonical, 'blogger', 'referral', path.stem, args.language, args.country, args.region, 'article')
body += f'\n<p><strong>Full version:</strong> <a href="{tracked}">{tracked}</a></p>'
payload = json.dumps({'kind': 'blogger#post', 'title': title, 'content': body, 'labels': ['AI', 'Automation', 'Agents']}).encode()
method = 'PUT' if args.update else 'POST'
post_id = f"/{registry[args.file]['id']}" if args.update else ''
url = f'https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts{post_id}?isDraft=false'
req = urllib.request.Request(url, data=payload, headers={'Authorization': 'Bearer ' + access_token(), 'Content-Type': 'application/json'}, method=method)
for attempt in range(3):
    try:
        with urllib.request.urlopen(req, timeout=60) as response: result = json.loads(response.read())
        break
    except HTTPError as error:
        detail = error.read().decode('utf-8', 'replace')
        if error.code != 429 or attempt == 2:
            raise SystemExit(f'Blogger API HTTP {error.code}: {detail[-1000:]}')
        retry_after = error.headers.get('Retry-After')
        delay = int(retry_after) if retry_after and retry_after.isdigit() else 65 * (attempt + 1)
        time.sleep(min(delay, 130))
record = {k: result.get(k) for k in ('id', 'url', 'title')}; registry[args.file] = record
registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n'); print(json.dumps(record, ensure_ascii=False))
