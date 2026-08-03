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
  var storedAttribution = JSON.parse(sessionStorage.getItem('agentlab_attribution') || '{}');

  function bridgeUrl(path, content) {
    var url = new URL(path, window.location.href);
    var hasAttribution = false;
    ['utm_source', 'utm_medium', 'utm_campaign'].forEach(function (key) {
      var value = currentParams.get(key) || storedAttribution[key];
      if (value) { url.searchParams.set(key, value); hasAttribution = true; }
    });
    var contentValue = currentParams.get('utm_content') || storedAttribution.utm_content;
    if (contentValue || hasAttribution) url.searchParams.set('utm_content', content || contentValue || 'internal');
    return url.toString();
  }

  function ctaTopic(link) {
    var value = ((link.getAttribute('href') || '') + ' ' + (link.textContent || '')).toLowerCase();
    if (value.indexOf('telegram') >= 0 || value.indexOf('тг') >= 0) return 'telegram';
    if (value.indexOf('mail') >= 0 || value.indexOf('почт') >= 0 || value.indexOf('@') >= 0) return 'email';
    if (value.indexOf('crm') >= 0) return 'crm';
    if (value.indexOf('report') >= 0 || value.indexOf('отч') >= 0) return 'reports';
    return 'general';
  }

  function reach(name, params) {
    if (typeof window.ym === 'function') window.ym(110942679, 'reachGoal', name, params || {});
  }

  document.addEventListener('DOMContentLoaded', function () {
    var currentSlug = window.location.pathname.split('/').pop() || 'index.html';
    sessionStorage.setItem('agentlab_landing_page', sessionStorage.getItem('agentlab_landing_page') || window.location.href);
    sessionStorage.setItem('agentlab_article_slug', currentSlug.replace('.html', ''));
    if (currentParams.toString()) {
      var nextAttribution = Object.assign({}, storedAttribution);
      ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content'].forEach(function (key) {
        if (currentParams.get(key)) nextAttribution[key] = currentParams.get(key);
      });
      sessionStorage.setItem('agentlab_attribution', JSON.stringify(nextAttribution));
    }
    document.querySelectorAll('a[href]').forEach(function (link) {
      var href = link.getAttribute('href') || '';
      if (href.indexOf('https://agentlabjournal.online/') !== 0 && href.indexOf('./') !== 0) return;
      if (href.indexOf('#') >= 0) return;
      var target = new URL(href, window.location.href);
      if (target.origin !== window.location.origin || !target.pathname.endsWith('.html')) return;
      var content = (target.pathname.split('/').pop() || 'internal').replace('.html', '');
      link.href = bridgeUrl(target.pathname + target.search, content);
      if (target.pathname.indexOf('lead-intake.html') >= 0) {
        link.dataset.ctaTopic = ctaTopic(link);
        link.dataset.articleSlug = currentSlug.replace('.html', '');
      }
      link.addEventListener('click', function () {
        reach('article_internal_click', { target: content, source: 'site' });
      });
    });

    document.querySelectorAll('a.service-action[href*="lead-intake.html"]').forEach(function (link) {
      link.dataset.ctaTopic = link.dataset.ctaTopic || ctaTopic(link);
    });

    var current = currentSlug;
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
    sessionStorage.setItem('agentlab_cta_topic', 'general');
    cta.className = 'content-bridge-cta';
    cta.dataset.ctaTopic = 'general';
    cta.dataset.articleSlug = current.replace('.html', '');
    cta.innerHTML = '<strong>Хотите проверить такой процесс у себя?</strong><a class="service-action" data-cta-topic="general" data-article-slug="' + current.replace('.html', '') + '" href="' + bridgeUrl('lead-intake.html', current.replace('.html', '') + '-cta') + '">Показать мой процесс →</a>';
    section.appendChild(cta);
    article.insertBefore(section, article.querySelector('.service-note') || null);
  });
})();
