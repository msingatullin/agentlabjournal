(function () {
  'use strict';

  var articleMap = {
    'guide-telegram-ai-agent.html': [
      ['Как письмо может заставить агента нарушить правила', 'guide-prompt-injection.html'],
      ['Личный AI-агент на VPS: Telegram, память и контроль действий', 'guide-personal-ai-agent.html']
    ],
    'guide-prompt-injection.html': [
      ['Как AI-агент в Telegram перестаёт быть тупым автоответчиком', 'guide-telegram-ai-agent.html'],
      ['Как превратить почтовый ящик в очередь задач', 'guide-email-automation.html']
    ],
    'guide-email-automation.html': [
      ['Как AI-агент в Telegram перестаёт быть тупым автоответчиком', 'guide-telegram-ai-agent.html'],
      ['Личный AI-агент на VPS: Telegram, память и контроль действий', 'guide-personal-ai-agent.html']
    ],
    'guide-personal-ai-agent.html': [
      ['Как AI-агент в Telegram перестаёт быть тупым автоответчиком', 'guide-telegram-ai-agent.html'],
      ['Как не утонуть в сотне роликов про AI', 'guide-notebooklm-workflow.html']
    ],
    'guide-notebooklm-workflow.html': [
      ['Как мы строим AI-систему, которая сама себя улучшает', 'article-hermes.html'],
      ['Личный AI-агент на VPS: Telegram, память и контроль действий', 'guide-personal-ai-agent.html']
    ],
    'article-hermes.html': [
      ['Личный AI-агент на VPS: Telegram, память и контроль действий', 'guide-personal-ai-agent.html'],
      ['Как письмо может заставить агента нарушить правила', 'guide-prompt-injection.html']
    ]
  };

  var currentParams = new URLSearchParams(window.location.search);
  var hasTelegramAttribution = currentParams.get('utm_source') === 'telegram';

  function bridgeUrl(path, content) {
    var url = new URL(path, window.location.href);
    if (!hasTelegramAttribution) return url.toString();
    url.searchParams.set('utm_source', 'telegram');
    url.searchParams.set('utm_medium', 'channel');
    url.searchParams.set('utm_campaign', 'pelmeni');
    url.searchParams.set('utm_content', content);
    return url.toString();
  }

  function reach(name, params) {
    if (typeof window.ym === 'function') window.ym(110942679, 'reachGoal', name, params || {});
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('a[href]').forEach(function (link) {
      var href = link.getAttribute('href') || '';
      if (!hasTelegramAttribution) return;
      if (href.indexOf('https://agentlabjournal.online/') !== 0 && href.indexOf('./') !== 0) return;
      if (href.indexOf('#') >= 0 || href.indexOf('utm_source=') >= 0) return;
      var target = new URL(href, window.location.href);
      if (target.origin !== window.location.origin || !target.pathname.endsWith('.html')) return;
      var content = (target.pathname.split('/').pop() || 'internal').replace('.html', '');
      link.href = bridgeUrl(target.pathname + target.search, content);
      link.addEventListener('click', function () {
        reach('article_internal_click', { target: content, source: 'site' });
      });
    });

    var current = window.location.pathname.split('/').pop() || 'index.html';
    var related = articleMap[current];
    var article = document.querySelector('main.article');
    if (!article || !related || article.querySelector('[data-content-bridge]')) return;

    var section = document.createElement('section');
    section.className = 'content-bridge';
    section.setAttribute('data-content-bridge', 'related');
    section.innerHTML = '<p class="eyebrow">СЛЕДУЮЩИЙ ШАГ</p><h2>Читайте также</h2><div class="content-bridge-links"></div>';
    var links = section.querySelector('.content-bridge-links');
    related.forEach(function (item) {
      var a = document.createElement('a');
      a.className = 'content-bridge-link';
      a.href = bridgeUrl(item[1], current.replace('.html', '') + '-related');
      a.textContent = item[0] + ' →';
      a.addEventListener('click', function () {
        reach('related_article_click', { from: current, to: item[1] });
      });
      links.appendChild(a);
    });
    var cta = document.createElement('div');
    cta.className = 'content-bridge-cta';
    cta.innerHTML = '<strong>Хотите проверить такой процесс у себя?</strong><a class="service-action" href="' + bridgeUrl('lead-intake.html', current.replace('.html', '') + '-cta') + '">Показать мой процесс →</a>';
    section.appendChild(cta);
    article.insertBefore(section, article.querySelector('.service-note') || null);
  });
})();
