#!/usr/bin/env python3
"""Enforce the fixed CTA order for one or all Russian articles."""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TELEGRAM = re.compile(r'\s*<a href="https://t\.me/pelmenews.*?</a>', re.S)
AUTOMATION = re.compile(r'\s*(?:<aside class="automation-article-cta".*?</aside>|<div aria-label="Заказать автоматизацию".*?</div>\s*<!-- CTA_END -->)', re.S)

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
        block = '''    <div aria-label="Заказать автоматизацию" style="margin:40px 0;padding:32px 24px;background:#0B1120;border:2px solid #00D4AA;border-radius:16px;box-shadow:0 8px 32px rgba(0,212,170,0.15);color:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;text-align:center"><div style="width:56px;height:56px;background:#00D4AA;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;margin-bottom:16px"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0B1120" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg></div><div style="font-size:20px;font-weight:800;margin-bottom:10px;line-height:1.3;color:#fff">Нужна такая автоматизация?</div><div style="font-size:15px;color:#94A3B8;line-height:1.5;margin-bottom:24px">Разработаем бота, интеграцию или AI-систему под ваши задачи. От ТЗ до запуска — берём всё на себя.</div><a href="contacts.html" style="display:inline-block;background:#00D4AA;color:#0B1120;text-decoration:none;font-weight:800;font-size:15px;padding:14px 32px;border-radius:10px;width:100%;max-width:280px;box-sizing:border-box;text-align:center">Обсудить проект</a></div><!-- CTA_END -->\n'''
        marker = '      <footer class="article-footer">'
        text = text.replace(marker, block + marker, 1) if marker in text else text.replace('    </article>', block + '    </article>', 1)
    path.write_text(text)
    return True

paths = [ROOT / sys.argv[1]] if len(sys.argv) > 1 else sorted(ROOT.glob('*.html'))
changed = sum(normalize(p) for p in paths if p.name not in {'index.html', 'contacts.html'} and not p.name.startswith('en-'))
print(f'CTA_ORDER_GATE: normalized {changed} articles')
