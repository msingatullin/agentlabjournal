(function () {
  var form = document.getElementById('lead-form'), status = document.getElementById('lead-status');
  if (!form || !status) return;
  var keys = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content'];
  var params = new URLSearchParams(location.search);
  var stored = JSON.parse(sessionStorage.getItem('agentlab_attribution') || '{}');
  var current = {};
  keys.forEach(function (key) { if (params.get(key)) current[key] = params.get(key); });
  var attribution = Object.assign({}, stored, current);
  sessionStorage.setItem('agentlab_attribution', JSON.stringify(attribution));
  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    var d = Object.fromEntries(new FormData(form)), button = form.querySelector('button');
    button.disabled = true;
    status.textContent = document.documentElement.lang === 'en' ? 'Sending…' : 'Отправляем…';
    var payload = {
      name: d.name, phone: d.contact, object: d.channel, comment: d.process,
      source: 'agentlabjournal', page: location.href,
      utm: {
        source: attribution.utm_source || 'direct', medium: attribution.utm_medium || 'none',
        campaign: attribution.utm_campaign || 'none', content: attribution.utm_content || 'none',
        article: sessionStorage.getItem('agentlab_article_slug') || '',
        cta_topic: sessionStorage.getItem('agentlab_cta_topic') || ''
      }
    };
    try {
      var response = await fetch('https://api.grifun.ru/api/leads', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
      });
      if (!response.ok) throw Error('request failed');
      form.reset();
      if (typeof window.ym === 'function') window.ym(110942679, 'reachGoal', 'lead_submitted');
      location.href = 'thanks.html';
    } catch (_) {
      status.textContent = document.documentElement.lang === 'en' ? 'Could not send. Please write to @msrzn007.' : 'Не удалось отправить. Напишите в Telegram: @msrzn007.';
    } finally { button.disabled = false; }
  });
})();
