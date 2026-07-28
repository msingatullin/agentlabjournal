#!/usr/bin/env python3
"""Enforce the fixed CTA order for one or all Russian articles."""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TELEGRAM = re.compile(r'\s*<a href="https://t\.me/pelmenews.*?</a>', re.S)
AUTOMATION = re.compile(r'\s*<aside class="automation-article-cta".*?</aside>', re.S)

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
        block = '''    <aside class="automation-article-cta" aria-label="Заказать автоматизацию"><div class="automation-article-cta__icon" aria-hidden="true"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><path d="M8 16h.01M16 16h.01"/></svg></div><div class="automation-article-cta__content"><div class="automation-article-cta__title">Нужна такая автоматизация?</div><div class="automation-article-cta__text">Разработаем бота, интеграцию или AI-систему под ваши задачи. От ТЗ до запуска.</div></div><a class="automation-article-cta__button" href="contacts.html">Обсудить проект</a></aside>\n'''
        marker = '      <footer class="article-footer">'
        text = text.replace(marker, block + marker, 1) if marker in text else text.replace('    </article>', block + '    </article>', 1)
    path.write_text(text)
    return True

paths = [ROOT / sys.argv[1]] if len(sys.argv) > 1 else sorted(ROOT.glob('*.html'))
changed = sum(normalize(p) for p in paths if p.name not in {'index.html', 'contacts.html'} and not p.name.startswith('en-'))
print(f'CTA_ORDER_GATE: normalized {changed} articles')
