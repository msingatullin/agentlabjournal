#!/usr/bin/env python3
"""Render the AI LIVE Pulse ticker strip for the website header."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED_PATH = ROOT / 'ai-live-feed.json'


def render_live_strip() -> str:
    if not FEED_PATH.is_file():
        return ''
    data = json.loads(FEED_PATH.read_text(encoding='utf-8'))
    status = data.get('status', {})
    benchmark = data.get('benchmark', {})
    signals = data.get('signals', [])

    items_html = []

    # 1. Operational status
    s_label = escape(status.get('label', 'AI STATUS'))
    s_msg = escape(status.get('message', 'OPERATIONAL'))
    items_html.append(
        f'<div class="live-strip__item live-strip__status"><span class="live-strip__pulse-dot"></span><span class="live-strip__badge">[ {s_label} ]</span><span class="live-strip__text">{s_msg}</span></div>'
    )

    # 2. Benchmark top
    if benchmark:
        b_label = escape(benchmark.get('label', 'ARENA'))
        b_val = escape(benchmark.get('value', ''))
        items_html.append(
            f'<div class="live-strip__item live-strip__benchmark"><span class="live-strip__badge live-strip__badge--metric">[ {b_label} ]</span><span class="live-strip__text">{b_val}</span></div>'
        )

    # 3. Dynamic breaking signals
    for sig in signals:
        tag = escape(sig.get('tag', 'LIVE'))
        t = escape(sig.get('time', ''))
        title = escape(sig.get('title', ''))
        link = escape(sig.get('link', '#'))
        items_html.append(
            f'<div class="live-strip__item"><span class="live-strip__badge">[ {tag} ]</span><span class="live-strip__time">{t}</span><a class="live-strip__link" href="{link}">{title}</a></div>'
        )

    full_inner = ' '.join(items_html)

    return (
        '<div class="live-strip" role="region" aria-label="AI Live Radar">\n'
        '  <div class="live-strip__label">\n'
        '    <span class="live-strip__pulse-icon"></span>\n'
        '    <strong>AI LIVE</strong>\n'
        '  </div>\n'
        '  <div class="live-strip__viewport">\n'
        '    <div class="live-strip__track">\n'
        f'      {full_inner}\n'
        '      <span class="live-strip__sep">///</span>\n'
        f'      {full_inner}\n'
        '    </div>\n'
        '  </div>\n'
        '</div>'
    )


if __name__ == '__main__':
    print(render_live_strip())
