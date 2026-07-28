#!/usr/bin/env python3
"""Add the Telegram channel CTA to every Russian article once."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CTA = '''
      <aside class="telegram-article-cta" aria-label="Telegram-канал Agent Lab Journal">
        <a href="https://t.me/pelmenews?utm_source=agentlabjournal&utm_medium=article&utm_campaign=telegram_channel&utm_content=article_footer" target="_blank" rel="noopener noreferrer">
          <span class="telegram-article-cta__icon" aria-hidden="true">↗</span>
          <span><strong>Читайте Agent Lab в Telegram</strong><small>Практика AI, автоматизации и разборы новых инструментов</small></span>
          <span class="telegram-article-cta__arrow" aria-hidden="true">→</span>
        </a>
      </aside>
'''

changed = 0
for page in ROOT.glob("*.html"):
    text = page.read_text(errors="ignore")
    if "reading-meta" not in text or "telegram-article-cta" in text:
        continue
    if "</article>" not in text:
        continue
    page.write_text(text.replace("</article>", CTA + "    </article>", 1))
    changed += 1
print(f"TELEGRAM_ARTICLE_CTA: updated {changed} articles")
