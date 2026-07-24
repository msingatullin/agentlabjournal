"""Publish an English article to Hashnode."""
from argparse import ArgumentParser
from html.parser import HTMLParser
from pathlib import Path
import json, os, re, urllib.request
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parent.parent

class Markdown(HTMLParser):
    def __init__(self):
        super().__init__(); self.out=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style','noscript'): self.skip += 1
        if self.skip: return
        if tag in ('h1','h2','h3'): self.out.append('\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'p': self.out.append('\n')
        elif tag == 'li': self.out.append('\n- ')
        elif tag == 'pre': self.out.append('\n```\n')
    def handle_endtag(self, tag):
        if tag in ('script','style','noscript') and self.skip: self.skip -= 1
        if not self.skip and tag == 'pre': self.out.append('\n```\n')
    def handle_data(self, data):
        if not self.skip: self.out.append(data)

parser = ArgumentParser(); parser.add_argument('--file', required=True); args = parser.parse_args()
token = os.environ.get('HASHNODE_PAT','').strip()
publication = os.environ.get('HASHNODE_PUBLICATION_ID','').strip()
if not token or not publication: raise SystemExit('HASHNODE_PAT or HASHNODE_PUBLICATION_ID is missing')
path = ROOT / args.file
registry_path = ROOT / 'hashnode-published.json'
registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
if args.file in registry:
    print(json.dumps(registry[args.file], ensure_ascii=False)); raise SystemExit(0)
text = path.read_text()
match = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S | re.I)
if not match: raise SystemExit('Article title not found')
title = re.sub(r'<[^>]+>', '', match.group(1)).strip()
desc = re.search(r'<meta name="description" content="([^"]*)"', text, re.I)
parser_html = Markdown(); parser_html.feed(text)
body = re.sub(r'\n{3,}', '\n\n', ''.join(parser_html.out)).strip()
canonical = f'https://agentlabjournal.online/{args.file}'
tracked = canonical + '?utm_source=hashnode&utm_medium=referral&utm_campaign=agentlabjournal'
body += f'\n\n---\n\n**Original article:** {tracked}\n'
lookup = 'query { publication(host: "agentlabjournal.hashnode.dev") { posts(first: 100) { edges { node { id title slug url content { markdown } } } } } }'
lookup_request = urllib.request.Request(os.environ.get('HASHNODE_GRAPHQL_ENDPOINT','https://gql-beta.hashnode.com/'),
    data=json.dumps({'query':lookup}).encode(),
    headers={'Content-Type':'application/json','Authorization':token,'User-Agent':'AgentLabJournal/1.0'})
with urllib.request.urlopen(lookup_request, timeout=60) as response: existing = json.loads(response.read())
for edge in existing.get('data',{}).get('publication',{}).get('posts',{}).get('edges',[]):
    post = edge.get('node',{})
    if canonical in (post.get('content',{}).get('markdown') or ''):
        registry[args.file] = {k: post.get(k) for k in ('id','title','slug','url')}
        registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(registry[args.file], ensure_ascii=False)); raise SystemExit(0)
query = 'mutation Draft($input: CreateDraftInput!) { createDraft(input: $input) { draft { id title slug } } }'
variables = {'input': {'publicationId': publication, 'title': title, 'contentMarkdown': body,
    'originalArticleURL': canonical,
    'slug': path.stem, 'tags': [{'slug':'ai','name':'AI'}, {'slug':'automation','name':'Automation'}, {'slug':'agents','name':'Agents'}]}}
request = urllib.request.Request(os.environ.get('HASHNODE_GRAPHQL_ENDPOINT','https://gql-beta.hashnode.com/'),
    data=json.dumps({'query':query,'variables':variables}).encode(),
    headers={'Content-Type':'application/json','Authorization':token,'User-Agent':'AgentLabJournal/1.0'})
try:
    with urllib.request.urlopen(request, timeout=60) as response: result = json.loads(response.read())
except HTTPError as error:
    detail = error.read().decode('utf-8', errors='replace')
    try:
        payload = json.loads(detail)
        messages = [item.get('message', '') for item in payload.get('errors', [])]
        detail = '\n'.join(messages)
    except json.JSONDecodeError:
        pass
    raise SystemExit(f'Hashnode API HTTP {error.code}: {detail[-3000:]}')
if result.get('errors'): raise SystemExit(json.dumps(result['errors'], ensure_ascii=False))
draft = result['data']['createDraft']['draft']
publish_query = 'mutation Publish($input: PublishDraftInput!) { publishDraft(input: $input) { post { id title slug url } } }'
publish_request = urllib.request.Request(os.environ.get('HASHNODE_GRAPHQL_ENDPOINT','https://gql-beta.hashnode.com/'),
    data=json.dumps({'query':publish_query,'variables':{'input':{'draftId':draft['id']}}}).encode(),
    headers={'Content-Type':'application/json','Authorization':token,'User-Agent':'AgentLabJournal/1.0'})
with urllib.request.urlopen(publish_request, timeout=60) as response: published = json.loads(response.read())
if published.get('errors'): raise SystemExit(json.dumps(published['errors'], ensure_ascii=False))
post = published['data']['publishDraft']['post']; registry[args.file] = post
registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(post, ensure_ascii=False))
