#!/usr/bin/env python3
"""Project agent: verify podcast feed delivery prerequisites for Yandex Music."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path('/root/agentlabjournal')
LIVE_RSS = 'https://agentlabjournal.online/podcast-rss.xml'
ALBUM = 'https://music.yandex.ru/album/43370492'


def http(url: str, method: str = 'GET') -> dict:
    request = urllib.request.Request(url, method=method, headers={'User-Agent': 'AgentLabPodcastYandexAgent/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return {'status': response.status, 'content_type': response.headers.get('Content-Type', '')}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--guid', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    state = {'agent': 'yandex-music-monitor', 'guid': args.guid, 'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'status': 'blocked', 'yandex_ingestion': 'not_confirmable_via_public_api'}
    live = http(LIVE_RSS)
    rss_text = urllib.request.urlopen(urllib.request.Request(LIVE_RSS, headers={'User-Agent': 'AgentLabPodcastYandexAgent/1.0'}), timeout=30).read()
    root = ET.fromstring(rss_text)
    item = next((item for item in root.findall('./channel/item') if item.findtext('guid') == args.guid), None)
    if item is None:
        state['reason'] = 'episode guid is absent from live RSS'
    else:
        enclosure = item.find('enclosure')
        audio_url = enclosure.attrib.get('url', '') if enclosure is not None else ''
        audio = http(audio_url, 'HEAD') if audio_url else {'status': 0, 'content_type': ''}
        album = http(ALBUM)
        state.update({'status': 'feed_ready' if live['status'] == 200 and audio['status'] == 200 and album['status'] == 200 else 'blocked', 'live_rss': live, 'audio': audio, 'album': album, 'audio_url': audio_url, 'note': 'RSS передан; факт отображения новой серии в каталоге Яндекс Музыки требует отдельной проверки в кабинете/приложении.'})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(state, ensure_ascii=False))
    return 0 if state['status'] == 'feed_ready' else 1


if __name__ == '__main__':
    raise SystemExit(main())
