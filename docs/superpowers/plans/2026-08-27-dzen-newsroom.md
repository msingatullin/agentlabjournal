# Agent Lab Dzen Newsroom Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Launch a fail-closed 15–20 item/day Dzen news pipeline with original illustrated articles, website CTA links, and Dzen interlinking.

**Architecture:** Extend the existing website-first RSS pipeline with a validated newsroom queue and Dzen URL registry. Build and verify one complete live canary before enabling the 18-slot scheduler.

**Tech Stack:** Python 3, static HTML, RSS 2.0, JSON state, systemd, GitHub Pages, Yandex.Webmaster API.

**Spec:** `docs/superpowers/specs/2026-08-27-dzen-newsroom-design.md`

## Global Constraints

- 18 daily slots between 08:00 and 23:00 MSK.
- Every item uses a current primary source and stored evidence.
- Every item has a unique 16:9 image of at least 1200×675.
- Publication fails closed on evidence, duplicate, image, SEO, link, or RSS errors.
- Scheduled automation stays disabled until a real Dzen canary is visually verified.

---

### Task 1: Correct RSS rich content

**Files:**
- Modify: `scripts/build-dzen-rss.py`
- Modify: `tests/test_build_dzen_rss.py`

**Interfaces:**
- Consumes: article canonical URL, H1, `og:image`, body links.
- Produces: `content:encoded` with `<figure><img>` and preserved safe `<a>` tags.

- [ ] Add a failing fixture assertion for a clickable CTA and lead figure.
- [ ] Run `python3 tests/test_build_dzen_rss.py` and confirm the new assertion fails.
- [ ] Preserve safe absolute/relative anchors and inject the lead image as the first figure.
- [ ] Reject unsupported schemes and escape attributes.
- [ ] Run the RSS tests and an XML contract inspection.
- [ ] Commit the isolated RSS correction.

### Task 2: Add newsroom validation and state

**Files:**
- Create: `scripts/dzen-newsroom.py`
- Create: `tests/test_dzen_newsroom.py`
- Create: `dzen-newsroom.json`
- Create: `dzen-publication-registry.json`

**Interfaces:**
- Produces: `validate`, `enqueue`, `due`, `mark-published`, and `register-dzen-url` commands.

- [ ] Write failing tests for exact/near duplicates, missing primary evidence,
  missing query passport, reused image, invalid dimensions, missing CTA, and
  missing related Dzen link.
- [ ] Run the tests and verify behavioral failures.
- [ ] Implement normalized hashes, similarity threshold, image inspection,
  queue transitions, and stable publication IDs.
- [ ] Run the focused test suite and commit.

### Task 3: Create the canary news package

**Files:**
- Create: one dated evidence record under `raw/seo/agentlab/` or linked source evidence.
- Create: one public news HTML page and one unique cover under `assets/news/`.
- Modify: `seo-query-map.json`, `homepage-covers.json`, `sitemap.xml`, `guides.html`, `llms.txt`.

**Interfaces:**
- Consumes: current primary source, measured query passport, verified Dzen URLs.
- Produces: a public canary page accepted by newsroom and publication gates.

- [ ] Select a current primary-source story and store its evidence.
- [ ] Build an original useful article with explicit uncertainty and source attribution.
- [ ] Create a unique 1600×900 editorial image and record provenance.
- [ ] Add site CTA and 1–3 verified Dzen related links.
- [ ] Run SEO, evidence, newsroom, and publication gates.
- [ ] Commit and push the canary.

### Task 4: Live canary and Dzen verification

**Files:**
- Modify: `dzen-publication-registry.json`
- Modify: `wiki/projects/dzen-content-network.md` outside the repository.

**Interfaces:**
- Consumes: deployed page and RSS item.
- Produces: verified Dzen URL and visual verification record.

- [ ] Wait for successful GitHub Pages deployment.
- [ ] Verify live HTML, image, RSS figure, enclosure, CTA, and Dzen links.
- [ ] Submit the canonical URL to Yandex.Webmaster and record task ID/quota.
- [ ] Wait for Dzen import; verify image, formatting, links, and restriction state in the authenticated browser.
- [ ] Register the Dzen URL and commit the registry.

### Task 5: Enable 18-slot daily scheduling

**Files:**
- Create: `scripts/run-dzen-newsroom.py`
- Create: `tests/test_run_dzen_newsroom.py`
- Create: `/etc/systemd/system/agentlab-dzen-newsroom.service`
- Create: `/etc/systemd/system/agentlab-dzen-newsroom.timer`

**Interfaces:**
- Consumes: validated queued packages and publication registry.
- Produces: one idempotent website/RSS publication per due slot.

- [ ] Write failing scheduler tests for 18 slots, missed-run catch-up, stable IDs,
  empty queue, and failed-gate behavior.
- [ ] Implement one-item-per-slot fail-closed publishing.
- [ ] Run focused and regression suites.
- [ ] Install units with the timer disabled.
- [ ] Run one dry-run and one real canary execution.
- [ ] Enable the timer only after Task 4 visual verification.
- [ ] Record runtime status and commit deployment documentation.

### Task 6: Fill the first daily queue

**Files:**
- Modify: `dzen-newsroom.json`
- Create: 17 additional validated article/image packages.

**Interfaces:**
- Produces: the first complete 18-item daily queue.

- [ ] Collect diverse current primary-source stories according to the editorial mix.
- [ ] Reject repeated events, headlines, angles, and images.
- [ ] Create query passports, articles, and unique images.
- [ ] Run every gate for all 18 packages.
- [ ] Publish according to slots and submit each canonical URL to recrawl.
- [ ] Record per-item website URL, Dzen URL, source, image provenance, and status.
