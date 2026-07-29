#!/usr/bin/env python3
"""Refresh the homepage's latest-articles block from published RU articles."""
from html import escape
from pathlib import Path
import re
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
SUMMARY_OVERRIDES = {
    'agent-failure-notifications.html': 'Как превратить техническую ошибку агента в понятное уведомление с причиной, последствиями, следующим действием и безопасной повторной диагностикой.',
    'agent-loop-budget-guards.html': 'Как ограничить агентный цикл по стоимости, времени и числу действий, сохранив понятную причину остановки и возможность безопасной диагностики.'
}
paths = []
topic_slugs = {item.get('slug') for item in __import__('json').loads((ROOT / 'article-topics.json').read_text())}
for path in ROOT.glob('*.html'):
    if path.name in {'index.html', 'lead-intake.html', 'contacts.html'} or (path.stem not in topic_slugs and 'reading-meta' not in path.read_text(errors='ignore')):
        continue
    text = path.read_text()
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S | re.I)
    lead = re.search(r'<p[^>]*class="[^"]*lead[^"]*"[^>]*>(.*?)</p>', text, re.S | re.I)
    if not h1:
        continue
    title = re.sub(r'<[^>]+>', '', h1.group(1)).strip()
    summary = re.sub(r'<[^>]+>', '', lead.group(1)).strip() if lead else SUMMARY_OVERRIDES.get(path.name, 'Практическое руководство Agent Lab Journal: проверяем решение на воспроизводимом сценарии и фиксируем критерии результата.')
    is_batch_article = path.stem not in topic_slugs and not path.name.startswith(('guide-', 'article-'))
    paths.append((is_batch_article, path.stat().st_mtime, path, title, summary))

paths.sort(reverse=True, key=lambda item: (item[0], item[1]))
cards = []
for index, (_, _, path, title, summary) in enumerate(paths[:4]):
    label = 'VOICE → TASK' if index == 0 else 'RULE → GATE'
    published = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
    cards.append(f'''      <article class="feature"{' style="margin-top:24px"' if index else ''}>
        <div class="feature-art"><div class="signal"></div><div class="task-card"><b>{label.split(' → ')[0]}</b><span>→</span><b>{label.split(' → ')[1]}</b></div></div>
        <div class="feature-body"><p class="meta">НОВЫЙ МАТЕРИАЛ · {published}</p><h3>{escape(title)}</h3><p>{escape(summary)}</p><a class="text-link" href="{escape(path.name)}">Открыть материал →</a></div>
      </article>''')

page = ROOT / 'index.html'
text = page.read_text()
pattern = r'    <section id="articles".*?    </section>\n    <section class="section"><div class="section-head"><p class="eyebrow">ПРАКТИКА</p>'
replacement = '    <section id="articles" class="section">\n      <div class="section-head"><p class="eyebrow" data-i18n="latest">ПОСЛЕДНЕЕ</p><h2 data-i18n="latestTitle">Материалы из рабочей лаборатории</h2></div>\n' + '\n'.join(cards) + '\n    </section>\n    <section class="section"><div class="section-head"><p class="eyebrow">ПРАКТИКА</p>'
updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
if count != 1:
    raise SystemExit('homepage latest block not found')
page.write_text(updated)
print(f'HOMEPAGE: refreshed {len(cards)} latest articles')
