#!/usr/bin/env python3
"""Render the AI LIVE Pulse ticker strip for the website header."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED_PATH = ROOT / "ai-live-feed.json"


def render_live_strip(lang: str = "ru", prefix: str = "") -> str:
    feed_filename = "ai-live-feed-en.json" if lang == "en" else "ai-live-feed.json"
    feed_path = ROOT / feed_filename
    if not feed_path.is_file():
        feed_path = FEED_PATH
    if not feed_path.is_file():
        return ""
    data = json.loads(feed_path.read_text(encoding="utf-8"))
    status = data.get("status", {})
    rates = data.get("rates", [])
    benchmark = data.get("benchmark", {})
    signals = data.get("signals", [])

    items_html = []

    # 1. Operational status
    s_label = escape(status.get("label", "AI STATUS"))
    s_msg = escape(status.get("message", "OPERATIONAL"))
    items_html.append(
        f'<div class="live-strip__item live-strip__status"><span class="live-strip__pulse-dot"></span><span class="live-strip__badge">[ {s_label} ]</span><span class="live-strip__text">{s_msg}</span></div>'
    )

    # 2. First rate (USD)
    if rates:
        r = rates[0]
        r_change_class = "live-strip__rate--up" if "+" in r.get("change", "") else "live-strip__rate--down"
        items_html.append(
            f'<div class="live-strip__item live-strip__rate"><span class="live-strip__icon">{escape(r.get("icon", ""))}</span><span class="live-strip__symbol">{escape(r.get("symbol", ""))}</span><span class="live-strip__val">{escape(r.get("value", ""))}</span><span class="{r_change_class}">{escape(r.get("change", ""))}</span></div>'
        )

    # 3. Benchmark
    if benchmark:
        b_label = escape(benchmark.get("label", "ARENA"))
        b_val = escape(benchmark.get("value", ""))
        items_html.append(
            f'<div class="live-strip__item live-strip__benchmark"><span class="live-strip__badge live-strip__badge--metric">[ {b_label} ]</span><span class="live-strip__text">{b_val}</span></div>'
        )

    # 4. Crypto rate (BTC)
    if len(rates) > 1:
        r = rates[1]
        r_change_class = "live-strip__rate--up" if "+" in r.get("change", "") else "live-strip__rate--down"
        items_html.append(
            f'<div class="live-strip__item live-strip__rate"><span class="live-strip__icon">{escape(r.get("icon", ""))}</span><span class="live-strip__symbol">{escape(r.get("symbol", ""))}</span><span class="live-strip__val">{escape(r.get("value", ""))}</span><span class="{r_change_class}">{escape(r.get("change", ""))}</span></div>'
        )

    # 5. Signals interleaved with remaining rates
    rate_idx = 2
    for sig in signals:
        tag = escape(sig.get("tag", "LIVE"))
        t = escape(sig.get("time", ""))
        title = escape(sig.get("title", ""))
        raw_link = sig.get("link", "#")
        is_ext = sig.get("external", False)

        if is_ext:
            link_target = ' target="_blank" rel="noopener noreferrer"'
            ext_icon = ' <span class="live-strip__ext-icon">↗</span>'
            link = escape(raw_link)
        else:
            link_target = ""
            ext_icon = ""
            link = escape(prefix + raw_link if not raw_link.startswith(("http", "/")) else raw_link)

        items_html.append(
            f'<div class="live-strip__item"><span class="live-strip__badge">[ {tag} ]</span><span class="live-strip__time">{t}</span><a class="live-strip__link" href="{link}"{link_target}>{title}{ext_icon}</a></div>'
        )

        if rate_idx < len(rates):
            r = rates[rate_idx]
            r_change_class = "live-strip__rate--up" if "+" in r.get("change", "") else "live-strip__rate--down"
            items_html.append(
                f'<div class="live-strip__item live-strip__rate"><span class="live-strip__icon">{escape(r.get("icon", ""))}</span><span class="live-strip__symbol">{escape(r.get("symbol", ""))}</span><span class="live-strip__val">{escape(r.get("value", ""))}</span><span class="{r_change_class}">{escape(r.get("change", ""))}</span></div>'
            )
            rate_idx += 1

    full_inner = " ".join(items_html)

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


if __name__ == "__main__":
    print(render_live_strip())
