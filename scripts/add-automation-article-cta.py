#!/usr/bin/env python3
"""Add the commercial automation CTA to Russian articles."""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CTA = '''    <aside class="automation-article-cta" aria-label="Заказать автоматизацию"><div class="automation-article-cta__icon" aria-hidden="true"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><path d="M8 16h.01M16 16h.01"/></svg></div><div class="automation-article-cta__content"><div class="automation-article-cta__title">Нужна такая автоматизация?</div><div class="automation-article-cta__text">Разработаем бота, интеграцию или AI-систему под ваши задачи. От ТЗ до запуска.</div></div><a class="automation-article-cta__button" href="contacts.html">Обсудить проект</a></aside>\n'''
telegram_re = re.compile(r'\s*<a href="https://t\.me/pelmenews.*?</a>', re.S)

def before_footer(text: str, block: str) -> str:
    marker = '      <footer class="article-footer">'
    return text.replace(marker, block + marker, 1) if marker in text else text.replace('    </article>', block + '    </article>', 1)

changed = 0
for path in sorted(ROOT.glob('*.html')):
    if path.name in {'index.html', 'contacts.html'} or path.name.startswith('en-'):
        continue
    text = path.read_text()
    if '<article' not in text or 'class="telegram-promo-block"' not in text or 'class="automation-article-cta"' in text:
        continue
    match = telegram_re.search(text)
    telegram = match.group(0).strip() if match else ''
    if match:
        text = text[:match.start()] + text[match.end():]
    length = len(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text)))
    if length < 800:
        continue
    text = before_footer(text, CTA)
    if length > 1500:
        paragraphs = list(re.finditer(r'</p>', text))
        if len(paragraphs) >= 3:
            pos = paragraphs[2].end()
            text = text[:pos] + '\n' + CTA + text[pos:]
    if telegram:
        text = before_footer(text, telegram + '\n')
    path.write_text(text)
    changed += 1
print(f'AUTOMATION_ARTICLE_CTA: updated {changed} Russian articles')
