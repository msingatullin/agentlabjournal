(function () {
  'use strict';

  var form = document.getElementById('lead-form');
  var status = document.getElementById('lead-status');
  if (!form || !status) return;

  var keys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content'];
  var params = new URLSearchParams(location.search);
  var stored = JSON.parse(sessionStorage.getItem('agentlab_attribution') || '{}');
  keys.forEach(function (key) { if (params.get(key)) stored[key] = params.get(key); });
  sessionStorage.setItem('agentlab_attribution', JSON.stringify(stored));

  var ctaElement = document.querySelector('[data-cta-topic]');
  var articleSlug = (ctaElement && ctaElement.getAttribute('data-article-slug')) ||
    sessionStorage.getItem('agentlab_article_slug') || (document.body.dataset.articleSlug || '');
  var ctaTopic = (ctaElement && ctaElement.getAttribute('data-cta-topic')) ||
    sessionStorage.getItem('agentlab_cta_topic') || 'general';
  var landingPage = sessionStorage.getItem('agentlab_landing_page') || location.href;
  sessionStorage.setItem('agentlab_landing_page', landingPage);

  function isPhoneChannel(channel) {
    var value = String(channel || '').toLowerCase();
    return value === 'phone' || value.indexOf('телефон') >= 0;
  }

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    var data = Object.fromEntries(new FormData(form));
    var submittedAt = new Date().toISOString();
    var button = form.querySelector('button');
    button.disabled = true;
    status.textContent = document.documentElement.lang === 'en' ? 'Sending…' : 'Отправляем…';

    // Canonical v1.2 record is collected regardless of the active transport.
    var v12 = {
      name: data.name,
      contact: data.contact,
      channel: data.channel,
      process: data.process,
      source: 'agentlabjournal',
      landing_page: landingPage,
      referrer: document.referrer || 'direct',
      article_slug: articleSlug,
      cta_topic: ctaTopic,
      utm_source: stored.utm_source || null,
      utm_medium: stored.utm_medium || null,
      utm_campaign: stored.utm_campaign || null,
      utm_content: stored.utm_content || null,
      submitted_at: submittedAt,
      page: location.href
    };

    // Current runtime is legacy. Do not invent a phone number: the legacy
    // endpoint accepts the explicit marker and the real contact remains in META.
    var legacyPayload = {
      name: v12.name,
      phone: isPhoneChannel(v12.channel) ? v12.contact : 'уточнить',
      object: v12.channel,
      comment: [
        v12.process,
        '',
        '---META---',
        'contact_type: ' + v12.channel,
        'contact_value: ' + v12.contact,
        'article: ' + v12.article_slug,
        'cta: ' + v12.cta_topic,
        'utm_source: ' + (v12.utm_source || ''),
        'utm_medium: ' + (v12.utm_medium || ''),
        'utm_campaign: ' + (v12.utm_campaign || ''),
        'utm_content: ' + (v12.utm_content || ''),
        'referrer: ' + v12.referrer,
        'submitted_at: ' + v12.submitted_at
      ].join('\n'),
      source: v12.source,
      page: v12.landing_page
    };

    try {
      var useV12 = Boolean(window.AGENTLAB_LEAD_ENDPOINT);
      var endpoint = window.AGENTLAB_LEAD_ENDPOINT || 'https://api.agentlabjournal.online/leads';
      var response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(useV12 ? v12 : legacyPayload)
      });
      if (!response.ok) throw Error('HTTP ' + response.status);
      var result = await response.json().catch(function () { return {}; });
      localStorage.setItem('agentlab_lead_v12_' + Date.now(), JSON.stringify({
        payload: v12,
        transport: useV12 ? 'v1.2' : 'legacy',
        result: result,
        stored_at: new Date().toISOString()
      }));
      sessionStorage.setItem('agentlab_lead_name', data.name || '');
      sessionStorage.setItem('agentlab_last_article', articleSlug);
      if (typeof window.ym === 'function') window.ym(110942679, 'reachGoal', 'lead_submitted');
      window.location.href = '/thanks.html?name=' + encodeURIComponent(v12.name || '');
    } catch (_) {
      status.textContent = document.documentElement.lang === 'en'
        ? 'Could not send. Please write to @msrzn007.'
        : 'Не удалось отправить заявку. Напишите в Telegram: @msrzn007.';
    } finally {
      button.disabled = false;
    }
  });
})();
