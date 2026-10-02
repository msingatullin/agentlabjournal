#!/usr/bin/env python3
"""Enforce the fixed CTA order for one or all Russian articles."""
from __future__ import annotations
import re
import sys
from pathlib import Path

from article_skeleton import MAX_PROMO, MAX_PROMO_CSS, SERVICE_NOTES, TELEGRAM_PROMO

ROOT = Path(__file__).resolve().parent.parent
TELEGRAM = re.compile(r'\s*<a href="https://t\.me/pelmenews[^>]*class="telegram-promo-block".*?</a>', re.S)
MAX = re.compile(r'\s*<a href="https://max\.ru/channel_AgentLab[^>]*class="max-promo-block".*?</a>', re.S)
AUTOMATION = re.compile(r'\s*(?:<aside class="automation-article-cta".*?</aside>|<aside class="service-note[^"]*".*?</aside>|<div aria-label="Заказать автоматизацию".*?</div>\s*<!-- CTA_END -->)', re.S)
ARTICLE_FOOTER = re.compile(r'[ \t]*<footer class="article-footer">')

def normalize(path: Path) -> bool:
    text = path.read_text()
    if 'reading-meta' not in text or '<article' not in text:
        return False
    telegram = TELEGRAM.search(text)
    telegram_html = telegram.group(0).strip() if telegram else TELEGRAM_PROMO
    max_match = MAX.search(text)
    max_html = max_match.group(0).strip() if max_match else MAX_PROMO
    text = MAX.sub('', TELEGRAM.sub('', text))
    text = AUTOMATION.sub('', text)
    promos = max_html + '\n' + telegram_html
    article = text.find('<article')
    header = text.find('<header class="article-header"')
    if header < 0:
        header = text.find('<header', article)
    header_end = text.find('</header>', header) if header >= 0 else -1
    if header_end >= 0:
        pos = header_end + len('</header>')
    else:
        pos = text.find('>', article) + 1
    text = text[:pos] + '\n' + promos + text[pos:]
    if 'max-promo.css' not in text:
        text = text.replace('</head>', MAX_PROMO_CSS.format(prefix='') + '\n</head>', 1)
    plain = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text))
    if len(plain) >= 1000:
        footer = ARTICLE_FOOTER.search(text)
        pos = footer.start() if footer else text.rfind('\n', 0, text.rfind('</article>')) + 1
        text = text[:pos] + SERVICE_NOTES + text[pos:]
    path.write_text(text)
    return True

paths = [ROOT / sys.argv[1]] if len(sys.argv) > 1 else sorted(ROOT.glob('*.html'))
changed = sum(normalize(p) for p in paths if p.name not in {'index.html', 'contacts.html'} and not p.name.startswith('en-'))
print(f'CTA_ORDER_GATE: normalized {changed} articles')
