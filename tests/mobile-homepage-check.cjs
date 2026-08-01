#!/usr/bin/env node
const { chromium } = require('playwright');

const viewports = [
  { width: 320, height: 900 },
  { width: 375, height: 900 },
  { width: 414, height: 900 },
  { width: 768, height: 1024 },
  { width: 1280, height: 800 },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  const articleResults = [];
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport });
    const consoleErrors = [];
    page.on('console', message => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });
    await page.goto('http://127.0.0.1:8765/', { waitUntil: 'networkidle' });
    await page.evaluate(async () => {
      document.documentElement.style.scrollBehavior = 'auto';
      for (let y = 0; y < document.body.scrollHeight; y += Math.max(320, window.innerHeight / 2)) {
        window.scrollTo(0, y);
        await new Promise(resolve => setTimeout(resolve, 60));
      }
      window.scrollTo(0, document.body.scrollHeight);
      await new Promise(resolve => setTimeout(resolve, 300));
      window.scrollTo(0, 0);
      await new Promise(resolve => setTimeout(resolve, 100));
    });
    const metrics = await page.evaluate(() => {
      const visible = element => {
        if (element.closest('details:not([open])') && element.tagName !== 'SUMMARY') return false;
        const style = getComputedStyle(element);
        const box = element.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' && box.width > 0 && box.height > 0;
      };
      const wrappedAffordances = [...document.querySelectorAll('nav a, summary, .editorial-link, .journal-cta a')]
        .filter(visible)
        .filter(element => {
          const style = getComputedStyle(element);
          return !style.whiteSpace.includes('nowrap') && element.getClientRects().length > 1;
        })
        .map(element => element.textContent.trim());
      const brokenImages = [...document.images]
        .filter(visible)
        .filter(image => !image.complete || image.naturalWidth === 0)
        .map(image => image.getAttribute('src'));
      return {
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        wrappedAffordances,
        brokenImages,
        mastheadHeight: Math.round(document.querySelector('.masthead').getBoundingClientRect().height),
        leadTop: Math.round(document.querySelector('.lead-story').getBoundingClientRect().top + window.scrollY),
      };
    });
    const label = `${viewport.width}x${viewport.height}`;
    await page.screenshot({ path: `/tmp/agentlab-homepage-${label}-fold.png`, fullPage: false });
    await page.screenshot({ path: `/tmp/agentlab-homepage-${label}.png`, fullPage: true });
    results.push({ viewport: label, ...metrics, consoleErrors });
    await page.close();
  }
  for (const width of [320, 768]) {
    for (const slug of [
      'llm-function-calling-provider-comparison',
      'audit-claude-code-hidden-reminders',
      'mcp-server-least-privilege',
      'prompt-injection-tool-output',
      'rag-corpus-change-regression',
      'agent-trace-data-minimization',
    ]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      await page.goto(`http://127.0.0.1:8765/${slug}.html`, { waitUntil: 'networkidle' });
      const metrics = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        coverLoaded: Boolean(document.querySelector('.article-cover img')?.naturalWidth),
      }));
      articleResults.push({ width, slug, ...metrics });
      await page.close();
    }
  }
  await browser.close();
  let failed = false;
  for (const row of results) {
    if (row.scrollWidth > row.clientWidth || row.wrappedAffordances.length || row.brokenImages.length || row.consoleErrors.length) failed = true;
  }
  for (const row of articleResults) {
    if (row.scrollWidth > row.clientWidth || !row.coverLoaded) failed = true;
  }
  console.log(JSON.stringify({ status: failed ? 'BLOCKED' : 'OK', results, articleResults }, null, 2));
  process.exit(failed ? 1 : 0);
})();
