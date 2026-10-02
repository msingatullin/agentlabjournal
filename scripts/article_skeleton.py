"""Canonical article skeleton fragments shared by the generator and CTA normalizer."""

MAX_PROMO_CSS = '<link rel="stylesheet" href="{prefix}max-promo.css">'

MAX_PROMO = '''<a href="https://max.ru/channel_AgentLab?utm_source=agentlabjournal&utm_medium=article&utm_campaign=max_channel&utm_content=article_footer" class="max-promo-block" target="_blank" rel="noopener noreferrer" aria-label="Самое важное из мира AI в канале MAX AgentLab">
  <span class="max-promo-block__icon" aria-hidden="true"></span>
  <span class="max-promo-block__content"><span class="max-promo-block__title">Самое важное из мира AI — в канале MAX AgentLab</span><span class="max-promo-block__desc">Отдельные разборы, инструменты и практические схемы</span></span>
  <span class="max-promo-block__arrow" aria-hidden="true">→</span>
</a>'''

TELEGRAM_PROMO = '''<a href="https://t.me/pelmenews?utm_source=agentlabjournal&utm_medium=article&utm_campaign=telegram_channel&utm_content=article_intro" class="telegram-promo-block" target="_blank" rel="noopener noreferrer" aria-label="Читайте Agent Lab в Telegram">
  <span class="telegram-promo-block__icon" aria-hidden="true"></span>
  <span class="telegram-promo-block__content">
    <span class="telegram-promo-block__title">Читайте Agent Lab в Telegram</span>
    <span class="telegram-promo-block__desc">Разборы, кейсы и новости о практических AI-агентах без лишней воды.</span>
  </span>
  <span class="telegram-promo-block__arrow" aria-hidden="true">→</span>
</a>'''

SERVICE_NOTES = '''<aside class="service-note" aria-label="Связаться по проекту">
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

EN_SERVICE_NOTE = '''<section class="service-note">
  <b>We publish what works for us—and implement the same solutions for your business.</b>
  We design AI automation, Telegram bots, chats, and AI agents for real-world processes.
  <a href="../contacts-en.html">Discuss your project →</a>
</section>
'''

RU_SITE_HEADER = '''<header class="site-header">
  <div class="container">
    <a class="site-name" href="./">Agent Lab Journal</a>
    <nav aria-label="Основная навигация">
      <a href="guides.html">Руководства</a>
      <a href="glossary.html">Глоссарий</a>
    </nav>
  </div>
</header>'''

EN_SITE_HEADER = '''<header class="site-header">
  <div class="container">
    <a class="site-name" href="./">Agent Lab Journal</a>
    <nav aria-label="Primary navigation">
      <a href="guides.html">Guides</a>
      <a href="../glossary.html">Glossary</a>
    </nav>
  </div>
</header>'''

RU_SITE_FOOTER = '''<footer class="site-footer">
  <div class="container">
    <p>Agent Lab Journal — практические материалы об AI-агентах и надёжных сценариях автоматизации.</p>
    <nav aria-label="Навигация в подвале">
      <a href="guides.html">Руководства</a>
      <a href="glossary.html">Глоссарий</a>
    </nav>
  </div>
</footer>'''

EN_SITE_FOOTER = '''<footer>
  <div class="container" style="display:flex;justify-content:space-between;width:100%;">
    <span>Agent Lab Journal</span>
    <span><a href="../privacy-ru.html">Privacy</a></span>
  </div>
</footer>'''
