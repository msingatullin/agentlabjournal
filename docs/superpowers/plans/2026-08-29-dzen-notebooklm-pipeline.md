# Dzen NotebookLM Publication Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed Dzen article preparation and daily RSS publication controller reviewed by NotebookLM.

**Architecture:** A focused Python controller owns package state, deterministic review parsing, daily rate limits and command orchestration. Existing article, cover, RSS, publication and recrawl scripts remain execution boundaries. Systemd runs preparation every four hours; public mutation requires explicit release mode and a validated approved package.

**Tech Stack:** Python 3 standard library, NotebookLM CLI, existing Agent Lab scripts, systemd.

**Spec:** `docs/superpowers/specs/2026-08-29-dzen-notebooklm-pipeline-design.md`

## Global Constraints

- Notebook ID is fixed to `7bbafa88-a8c4-44bf-9a17-77851f87d459`.
- Publication requires `APPROVE`, score `>=80`, matching draft SHA-256 and zero blocking issues.
- Maximum three revisions and one public release per Moscow date.
- Dry-run performs no public writes, git pushes or recrawl calls.
- Missed slots do not accumulate.

---

### Task 1: Deterministic package and review gate

**Files:**
- Create: `scripts/dzen-article-pipeline.py`
- Create: `tests/test_dzen_article_pipeline.py`

**Interfaces:**
- Produces: `draft_sha256()`, `validate_review()`, `can_publish_today()`, `transition()` and CLI commands `review`, `status`, `dry-run`.

- [ ] Write tests for approve, malformed review, hash mismatch, fourth revision and duplicate daily release.
- [ ] Run tests and verify expected failures.
- [ ] Implement the minimal state/review gate.
- [ ] Run tests and verify passes.

### Task 2: NotebookLM command boundary

**Files:**
- Modify: `scripts/dzen-article-pipeline.py`
- Modify: `tests/test_dzen_article_pipeline.py`

**Interfaces:**
- Produces: `build_review_prompt()` and `run_notebook_review()` with dependency-injected subprocess runner.

- [ ] Add failing tests proving the full draft, hash, sources and image brief enter the request and errors fail closed.
- [ ] Implement JSON extraction and review artifact persistence.
- [ ] Run focused tests.

### Task 3: Unique image and RSS consistency gates

**Files:**
- Modify: `scripts/dzen-article-pipeline.py`
- Modify: `scripts/build-dzen-rss.py`
- Modify: `tests/test_dzen_article_pipeline.py`
- Modify: `tests/test_build_dzen_rss.py`

- [ ] Add failing tests for reused image hashes/URLs and mismatched metadata surfaces.
- [ ] Implement fail-closed checks and deterministic time fixture.
- [ ] Run RSS and pipeline tests.

### Task 4: Scheduler and safe migration

**Files:**
- Create: `ops/systemd/agentlab-dzen-article-pipeline.service`
- Create: `ops/systemd/agentlab-dzen-article-pipeline.timer`
- Create: `scripts/install-dzen-article-pipeline.sh`
- Modify: `tests/test_dzen_article_pipeline.py`

- [ ] Add tests for four-hour timer, persistent=false anti-burst behavior and dry-run ExecStart.
- [ ] Implement units and installer that requires two dry-run receipts before disabling the obsolete timer.
- [ ] Run tests and shell syntax validation.

### Task 5: Verification

- [ ] Run all Dzen pipeline, newsroom and RSS tests.
- [ ] Run two dry-runs and compare idempotency receipts.
- [ ] Inspect git diff and systemd unit verification.
- [ ] Only when gates pass, install/enable new timer and disable/stop `hermes-dzen-send.timer`.
