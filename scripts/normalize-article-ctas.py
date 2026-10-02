#!/usr/bin/env python3
"""Enforce the fixed CTA order for one or all Russian articles."""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TELEGRAM = re.compile(r'\s*<a href="https://t\.me/pelmenews.*?</a>', re.S)
AUTOMATION = re.compile(r'\s*(?:<aside class="automation-article-cta".*?</aside>|<aside class="service-note[^"]*".*?</aside>|<div aria-label="Заказать автоматизацию".*?</div>\s*<!-- CTA_END -->)', re.S)

def normalize(path: Path) -> bool:
    text = path.read_text()
    if 'reading-meta' not in text or '<article' not in text:
        return False
    telegram = TELEGRAM.search(text)
    telegram_html = telegram.group(0).strip() if telegram else ''
    text = TELEGRAM.sub('', text)
    text = AUTOMATION.sub('', text)
    if not telegram_html:
        return False
    header = text.find('<header class="article-header"')
    header_end = text.find('</header>', header)
    if header >= 0 and header_end >= 0:
        pos = header_end + len('</header>')
        text = text[:pos] + '\n' + telegram_html + '\n' + text[pos:]
    else:
        text = text.replace('</article>', telegram_html + '\n    </article>', 1)
    plain = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text))
    if len(plain) >= 1000:
        block = '''<aside class="service-note" aria-label="Связаться по проекту">
  <div class="service-note__copy">
    <p class="service-note__label">Связь с Agent Lab</p>
    <p class="service-note__title">Внедрим такой контур в ваш процесс</p>
    <p class="service-note__text">Напишите инженеру Agent Lab в Telegram: опишите задачу, бота или интеграцию — предложим пилот с проверками и понятными границами.</p>
  </div>
  <a class="service-note__link" href="https://t.me/msrzn007?utm_source=journal&amp;utm_medium=article&amp;utm_campaign=service_note" target="_blank" rel="noopener">Написать в Telegram
    <svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M3 13 13 3M6 3h7v7"/></svg>
  </a>
</aside>
<aside class="service-note service-note--sitevisor" aria-label="Экспресс-аудит сайта">
  <div class="service-note__copy">
    <p class="service-note__label">SiteVisor</p>
    <p class="service-note__title">Проверьте техническое состояние и готовность вашего сайта к рекламе</p>
    <p class="service-note__text">Экспресс-аудит на SiteVisor.pro: индексация, скорость, разметка, аналитика и точки конверсии.</p>
  </div>
  <a class="service-note__link" href="https://sitevisor.pro/?utm_source=journal&amp;utm_medium=article&amp;utm_campaign=leadmagnet" target="_blank" rel="noopener">Экспресс-аудит на SiteVisor.pro
    <svg viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"><path d="M3 13 13 3M6 3h7v7"/></svg>
  </a>
</aside>
'''
        marker = '      <footer class="article-footer">'
        text = text.replace(marker, block + marker, 1) if marker in text else text.replace('    </article>', block + '    </article>', 1)
    path.write_text(text)
    return True

paths = [ROOT / sys.argv[1]] if len(sys.argv) > 1 else sorted(ROOT.glob('*.html'))
changed = sum(normalize(p) for p in paths if p.name not in {'index.html', 'contacts.html'} and not p.name.startswith('en-'))
print(f'CTA_ORDER_GATE: normalized {changed} articles')
