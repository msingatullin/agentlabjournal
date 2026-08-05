#!/usr/bin/env python3
"""Publish a validated daily RU podcast to MicroSrv, site RSS and Yandex's RSS source."""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path('/root/agentlabjournal')
MICRO = Path('/opt/microsaas-platform/podcasts')
BASE = 'https://agentlabjournal.online'
ALBUM = 'https://music.yandex.ru/album/43370492'


def duration(path: Path) -> str:
    value = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=nw=1:nk=1', str(path)], text=True).strip()
    seconds = max(1, int(float(value)))
    return f'{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not args.audio.is_file() or args.audio.stat().st_size < 100_000:
        raise SystemExit('audio validation failed')

    slug = f'podcast-{args.date}-ru'
    filename = f'agent-lab-journal-ru-{args.date}.mp3'
    page_name = f'{slug}.html'
    public_audio = f'https://microsrv.online/podcasts/{filename}'
    public_page = f'{BASE}/{page_name}'
    length = duration(args.audio)
    title_json = json.dumps(args.title, ensure_ascii=False)
    date_label = dt.date.fromisoformat(args.date).strftime('%-d %B %Y')
    page = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(args.title)} — Agent Lab Journal Podcast</title><meta name="description" content="{html.escape(args.summary)}"><link rel="canonical" href="{public_page}"><meta property="og:type" content="article"><meta property="og:title" content="{html.escape(args.title)}"><meta property="og:description" content="{html.escape(args.summary)}"><meta property="og:url" content="{public_page}"><meta property="og:image" content="{BASE}/podcast-cover.png"><link rel="stylesheet" href="style.css"><script type="application/ld+json">{{"@context":"https://schema.org","@type":"PodcastEpisode","name":{title_json},"url":"{public_page}","datePublished":"{args.date}T07:00:00+03:00","duration":"PT{length.replace(':','M',1).replace(':','S')}","inLanguage":"ru-RU","image":"{BASE}/podcast-cover.png","partOfSeries":{{"@type":"PodcastSeries","name":"Agent Lab Journal Podcast","url":"{BASE}/podcasts.html"}},"associatedMedia":{{"@type":"AudioObject","contentUrl":"{public_audio}","encodingFormat":"audio/mpeg"}}}}</script></head><body><header class="site-header"><a class="brand" href="./">Agent Lab Journal</a><nav><a href="podcasts.html">Подкасты</a><a href="contacts.html">Контакты</a></nav></header><main class="podcast-shell"><p class="eyebrow">AGENT LAB JOURNAL PODCAST · {html.escape(date_label.upper())}</p><h1>{html.escape(args.title)}</h1><p class="podcast-meta">Русский выпуск · {length} · {html.escape(date_label)}</p><p>{html.escape(args.summary)}</p><audio controls preload="metadata" src="{public_audio}"></audio><p><a class="primary" href="podcasts.html">Все выпуски →</a> <a class="text-link" href="podcast-rss.xml">Подписаться через RSS</a></p></main><footer><span>Agent Lab Journal</span></footer></body></html>'''
    item = f'''  <item><title>{html.escape(args.title)}</title><description>{html.escape(args.summary)}</description><link>{public_page}?utm_source=podcast&amp;utm_medium=rss&amp;utm_campaign=daily-ai-news&amp;utm_content=ru-{args.date.replace("-", "")}</link><guid isPermaLink="false">agentlabjournal-ru-{args.date}</guid><pubDate>{dt.datetime.fromisoformat(args.date).replace(tzinfo=dt.timezone(dt.timedelta(hours=3))).strftime("%a, %d %b %Y %H:%M:%S +0300")}</pubDate><itunes:duration>{length}</itunes:duration><itunes:episodeType>full</itunes:episodeType><enclosure url="{public_audio}" type="audio/mpeg" length="{args.audio.stat().st_size}" /></item>'''
    if args.dry_run:
        print(f'PAGE={page_name}\nAUDIO={public_audio}\nRSS_ITEM_READY=1\nDURATION={length}')
        return 0

    MICRO.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.audio, MICRO / filename)
    (ROOT / page_name).write_text(page, encoding='utf-8')
    rss = ROOT / 'podcast-rss.xml'
    rss_text = rss.read_text(encoding='utf-8')
    if f'agentlabjournal-ru-{args.date}' not in rss_text:
        rss.write_text(rss_text.replace('  <item>', item + '\n  <item>', 1), encoding='utf-8')
    sitemap = ROOT / 'sitemap.xml'
    sitemap_text = sitemap.read_text(encoding='utf-8')
    if public_page not in sitemap_text:
        sitemap.write_text(sitemap_text.replace('</urlset>', f'  <url><loc>{public_page}</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>\n</urlset>', 1), encoding='utf-8')
    subprocess.run(['git', 'add', page_name, 'podcast-rss.xml', 'sitemap.xml'], cwd=ROOT, check=True)
    subprocess.run(['git', 'commit', '-m', f'Publish daily podcast {args.date}'], cwd=ROOT, check=True)
    subprocess.run(['git', 'push', 'origin', 'HEAD'], cwd=ROOT, check=True)
    for url in (public_page, 'https://agentlabjournal.online/podcast-rss.xml'):
        subprocess.run(['/usr/bin/python3', str(ROOT / 'scripts/submit-yandex-recrawl.py'), '--url', url], cwd=ROOT, check=False)
    with urlopen(Request(public_audio, method='HEAD'), timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f'audio public check failed: HTTP {response.status}')
    with urlopen(Request(ALBUM, method='GET'), timeout=30) as response:
        print(f'YANDEX_MUSIC_ALBUM_HTTP={response.status}')
    print(f'PUBLISHED={public_page}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
