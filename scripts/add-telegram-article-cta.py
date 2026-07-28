#!/usr/bin/env python3
"""Add the Telegram channel CTA to every Russian article once."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CTA = '''
      <a href="https://t.me/pelmenews?utm_source=agentlabjournal&utm_medium=article&utm_campaign=telegram_channel&utm_content=article_intro" class="telegram-promo-block" target="_blank" rel="noopener noreferrer" aria-label="Читайте Agent Lab в Telegram">
        <span class="telegram-promo-block__icon" aria-hidden="true"><svg width="40" height="40" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="50" fill="#34AADF"/><path d="M22.5 50.5L72.5 28L60 72.5L45 57.5L72.5 28L22.5 50.5Z" fill="white" opacity="0.4"/><path d="M42.5 55L72.5 28L45 57.5L42.5 55Z" fill="white"/><path d="M38 62.5L42.5 55L45 57.5L38 62.5Z" fill="white"/><path d="M38 62.5L40.5 53.5L42.5 55L38 62.5Z" fill="#D2E5F1"/></svg></span>
        <span class="telegram-promo-block__content"><span class="telegram-promo-block__title">Читайте Agent Lab в Telegram</span><span class="telegram-promo-block__desc">Практика AI, автоматизации и разборы новых инструментов</span></span>
        <span class="telegram-promo-block__arrow" aria-hidden="true">→</span>
      </a>
'''

changed = 0
for page in ROOT.glob("*.html"):
    text = page.read_text(errors="ignore")
    if "reading-meta" not in text:
        continue
    if 'class="telegram-article-cta"' in text:
        old_start = text.find('      <aside class="telegram-article-cta"')
        old_end = text.find("      </aside>", old_start)
        if old_start >= 0 and old_end >= 0:
            text = text[:old_start] + text[old_end + len("      </aside>"):]
    if "</article>" not in text:
        continue
    if "<nav class=\"table-of-contents\"" in text:
        text = text.replace('<nav class="table-of-contents"', CTA + '      <nav class="table-of-contents"', 1)
    elif "</header>" in text:
        text = text.replace("</header>", "</header>" + CTA, 1)
    else:
        text = text.replace("</article>", CTA + "    </article>", 1)
    page.write_text(text)
    changed += 1
print(f"TELEGRAM_ARTICLE_CTA: updated {changed} articles")
