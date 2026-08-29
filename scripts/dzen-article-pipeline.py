#!/usr/bin/env python3
"""Fail-closed state and NotebookLM review gate for Dzen RSS articles."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable


NOTEBOOK_ID = "7bbafa88-a8c4-44bf-9a17-77851f87d459"
MIN_SCORE = 80
MAX_REVISIONS = 3
CODEX = "/usr/bin/codex"


def draft_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_review(review: Any, expected_hash: str) -> list[str]:
    if not isinstance(review, dict):
        return ["review_not_object"]
    errors: list[str] = []
    if review.get("reviewed_draft_sha256") != expected_hash:
        errors.append("reviewed_draft_hash_mismatch")
    if review.get("verdict") not in {"APPROVE", "REVISE", "BLOCKED"}:
        errors.append("review_verdict_invalid")
    score = review.get("score_0_100")
    if not isinstance(score, int) or not 0 <= score <= 100:
        errors.append("review_score_invalid")
    if not isinstance(review.get("blocking_issues"), list):
        errors.append("review_blocking_issues_invalid")
    if not isinstance(review.get("revision_instructions"), list):
        errors.append("review_revision_instructions_invalid")
    if not isinstance(review.get("citations"), list) or not review.get("citations"):
        errors.append("review_missing_citations")
    if review.get("verdict") == "APPROVE":
        if not isinstance(score, int) or score < MIN_SCORE:
            errors.append("approve_score_below_threshold")
        if review.get("blocking_issues"):
            errors.append("approve_has_blocking_issues")
    return errors


def transition(state: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    result = dict(state)
    verdict = review.get("verdict")
    if verdict == "APPROVE":
        result["status"] = "APPROVED"
        return result
    if verdict == "BLOCKED":
        result["status"] = "BLOCKED"
        return result
    attempts = int(result.get("revision_attempts", 0)) + 1
    result["revision_attempts"] = attempts
    result["status"] = "DEAD_LETTER" if attempts > MAX_REVISIONS else "REVISE"
    return result


def can_publish_today(state: dict[str, Any], now: dt.datetime) -> bool:
    if now.tzinfo is None:
        raise ValueError("publication clock requires timezone")
    moscow = now.astimezone(dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    return moscow not in set(state.get("published_dates", []))


def publication_slot_open(state: dict[str, Any], now: dt.datetime) -> bool:
    """Allow at most one completed publication per Moscow calendar date."""
    value = state.get("last_published_at")
    if not value:
        return True
    if now.tzinfo is None:
        raise ValueError("publication clock requires timezone")
    previous = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    moscow = dt.timezone(dt.timedelta(hours=3))
    return previous.astimezone(moscow).date() < now.astimezone(moscow).date()


def rss_day_reserved(root: Path, now: dt.datetime) -> bool:
    feed = root / "dzen-rss.xml"
    if not feed.exists():
        return False
    moscow = dt.timezone(dt.timedelta(hours=3))
    today = now.astimezone(moscow).date()
    try:
        tree = ET.parse(feed)
        dates = [parsedate_to_datetime(node.text) for node in tree.findall("./channel/item/pubDate") if node.text]
    except (ET.ParseError, TypeError, ValueError):
        return True
    return any(value.astimezone(moscow).date() == today for value in dates)


def build_autonomous_prompt(dry_run: bool) -> str:
    mode = "DRY RUN: prepare the next eligible future article even if today's publication slot is already used; do not treat today's slot as a blocker." if dry_run else "RELEASE CANDIDATE PREPARATION."
    return f"""You are the autonomous Dzen RSS newsroom operator for Agent Lab Journal.
Work only inside this isolated checkout. {mode}

Produce exactly one Russian news or analytical article package, or return BLOCKED. Never ask the owner questions.
Mandatory gates, in order:
1. Select one fresh, non-duplicate topic from a current official/primary source. Start with unused official URLs in article-source-candidates.json, verify the event date and source directly, and derive a brand-new slug. Never edit, refresh, re-cover or reuse any existing HTML page, package, slug, title or canonical URL. Reject advertising, announcements, lists, schedules and non-news blog material.
2. Create and validate a Wordstat query passport with measured demand, intent, canonical URL and cannibalization check. Unvalidated demand blocks release.
3. Write an evidence-based article without invented tests, quotes, dates or results. Preserve source URLs and collection dates.
4. Generate a new topic-specific unique image for this article. Never reuse an existing URL or SHA-256. Record prompt, path and hash; disclose AI use.
5. Upload the immutable full draft to NotebookLM {NOTEBOOK_ID}, wait for indexing, and request strict JSON review. Require matching SHA-256, verdict APPROVE, score_0_100 >= 80, citations and zero blocking issues. Apply no more than three revisions; otherwise BLOCKED.
6. Render HTML with title/H1 alignment, canonical, description, Article JSON-LD, datePublished, source links and the approved unique image. Update homepage-covers.json.
7. Run repository publication gates and build dzen-rss.xml. Verify RSS canonical, full text and unique enclosure URL.
8. Enforce one publication per Moscow calendar day. Missed four-hour runs never accumulate and never cause a burst.
9. PREPARE ONLY: never commit, git push, publish, wait on the public URL, or submit Yandex.Webmaster recrawl. The deterministic outer controller owns all external release actions after validating your files.
10. Write newsroom/dzen-autonomous-state.json and a package publication-receipt.json only from observed results.

Fail closed on any missing credential, source evidence, SEO measurement, image, NotebookLM approval, validation, push, public HTTP check, RSS check or recrawl acceptance. Do not weaken authentication, repository rules or gates. Do not expose secrets.
Return only JSON matching the supplied schema.
"""


def validate_prepared_candidate(root: Path, receipt: dict[str, Any], baseline_slugs: set[str]) -> list[str]:
    errors: list[str] = []
    slug = receipt.get("slug")
    if receipt.get("status") != "PREPARED":
        errors.append("candidate_not_prepared")
    if not isinstance(slug, str) or not slug:
        return errors + ["slug_missing"]
    if slug in baseline_slugs:
        return errors + ["slug_preexisting"]
    packages = sorted((root / "newsroom" / "packages").glob(f"*-{slug}"))
    if len(packages) != 1:
        return errors + ["package_missing_or_ambiguous"]
    package = packages[0]
    drafts = sorted(package.glob("draft-v*.md"))
    reviews = sorted(package.glob("notebooklm-review-v*.json"))
    if not drafts:
        errors.append("draft_missing")
    if not reviews:
        errors.append("review_missing")
    if drafts and reviews:
        draft = drafts[-1].read_text(encoding="utf-8")
        review = json.loads(reviews[-1].read_text(encoding="utf-8"))
        errors.extend(validate_review(review, draft_sha256(draft)))
        if review.get("verdict") != "APPROVE":
            errors.append("review_not_approved")
    brief_path = package / "image-brief.json"
    if not brief_path.exists():
        errors.append("image_brief_missing")
    else:
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        relative = brief.get("asset_path")
        image = root / relative if isinstance(relative, str) else None
        if image is None or not image.is_file():
            errors.append("image_missing")
        else:
            candidate_hash = file_sha256(image)
            if candidate_hash != receipt.get("image_sha256"):
                errors.append("image_hash_mismatch")
            for existing in (root / "assets").rglob("*"):
                if existing.is_file() and existing != image and existing.suffix.casefold() in {".png", ".jpg", ".jpeg", ".webp"}:
                    if file_sha256(existing) == candidate_hash:
                        errors.append("image_hash_reused")
                        break
    page = root / f"{slug}.html"
    if not page.exists():
        errors.append("html_missing")
    else:
        markup = page.read_text(encoding="utf-8")
        canonical = f'https://agentlabjournal.online/{slug}.html'
        if canonical not in markup:
            errors.append("canonical_mismatch")
    return errors


def wait_public(url: str, attempts: int = 40, delay: int = 15) -> None:
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "AgentLabDzenGate/1.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                if response.status == 200:
                    return
        except Exception:
            pass
        if attempt + 1 < attempts:
            time.sleep(delay)
    raise RuntimeError(f"public HTTP gate failed: {url}")


def release_candidate(checkout: Path, receipt_path: Path, receipt: dict[str, Any], now: dt.datetime) -> dict[str, Any]:
    slug = str(receipt["slug"])
    package = next(iter(sorted((checkout / "newsroom" / "packages").glob(f"*-{slug}"))))
    subprocess.run([sys.executable, "scripts/seo-query-gate.py", "--slug", slug, "--language", "ru"], cwd=checkout, check=True)
    subprocess.run([sys.executable, "scripts/build-dzen-rss.py", "--root", str(checkout)], cwd=checkout, check=True)

    brief = json.loads((package / "image-brief.json").read_text(encoding="utf-8"))
    allowed = {
        f"{slug}.html",
        str(Path(brief["asset_path"])),
        "homepage-covers.json",
        "seo-query-map.json",
        "dzen-rss.xml",
    }
    allowed_prefix = str(package.relative_to(checkout)) + "/"
    status = subprocess.run(["git", "status", "--porcelain"], cwd=checkout, text=True, capture_output=True, check=True).stdout
    changed = {line[3:] for line in status.splitlines() if len(line) > 3}
    forbidden = sorted(path for path in changed if path not in allowed and not path.startswith(allowed_prefix))
    if forbidden:
        raise RuntimeError("candidate changed forbidden paths: " + ",".join(forbidden))

    moscow = now.astimezone(dt.timezone(dt.timedelta(hours=3)))
    state = {
        "last_cycle_at": moscow.isoformat(),
        "last_cycle_mode": "release",
        "last_status": "RELEASE_PENDING",
        "last_slug": slug,
        "last_published_at": moscow.isoformat(),
        "published_dates": [moscow.date().isoformat()],
    }
    state_path = checkout / "newsroom" / "dzen-autonomous-state.json"
    save_json(state_path, state)
    subprocess.run(["git", "add", *sorted(allowed), allowed_prefix, "newsroom/dzen-autonomous-state.json"], cwd=checkout, check=True)
    subprocess.run(["git", "commit", "-m", f"Publish Dzen article: {slug}"], cwd=checkout, check=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=checkout, text=True, capture_output=True, check=True).stdout.strip()
    subprocess.run(["git", "push", "origin", "main"], cwd=checkout, check=True)

    canonical = f"https://agentlabjournal.online/{slug}.html"
    wait_public(canonical)
    recrawl_run = subprocess.run(
        [sys.executable, "scripts/submit-yandex-recrawl.py", "--url", canonical],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=True,
    )
    recrawl = json.loads(recrawl_run.stdout)
    if recrawl.get("status") != "accepted" or not recrawl.get("task_id"):
        raise RuntimeError("Yandex recrawl was not accepted")
    receipt.update({
        "status": "PUBLISHED",
        "published": True,
        "canonical_url": canonical,
        "reason": None,
        "commit": commit,
        "recrawl_task_id": recrawl["task_id"],
    })
    receipt["gates"].update({"git": True, "public_http": True, "recrawl": True})
    save_json(package / "publication-receipt.json", receipt)
    state["last_status"] = "PUBLISHED"
    save_json(state_path, state)
    save_json(receipt_path, receipt)
    subprocess.run(["git", "add", str((package / "publication-receipt.json").relative_to(checkout)), "newsroom/dzen-autonomous-state.json"], cwd=checkout, check=True)
    subprocess.run(["git", "commit", "-m", f"Record Dzen publication receipt: {slug}"], cwd=checkout, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=checkout, check=True)
    return receipt


def build_codex_command(checkout: Path, receipt: Path, dry_run: bool) -> list[str]:
    return [
        CODEX,
        "exec",
        "--ephemeral",
        "--sandbox",
        "danger-full-access",
        "--cd",
        str(checkout),
        "--output-schema",
        str(checkout / "newsroom" / "dzen-autonomous-receipt.schema.json"),
        "--output-last-message",
        str(receipt),
        "-",
    ]


def run_autonomous(checkout: Path, receipt: Path, dry_run: bool) -> int:
    state_path = checkout / "newsroom" / "dzen-autonomous-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    now = dt.datetime.now(dt.timezone.utc)
    if not dry_run and (not publication_slot_open(state, now) or rss_day_reserved(checkout, now)):
        save_json(receipt, {"status": "SKIPPED", "reason": "daily_limit", "published": False})
        return 0
    baseline_slugs = {page.stem for page in checkout.glob("*.html")}
    result = subprocess.run(
        build_codex_command(checkout, receipt, dry_run),
        input=build_autonomous_prompt(dry_run),
        text=True,
        timeout=3300,
    )
    if result.returncode:
        return result.returncode
    try:
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        errors = validate_prepared_candidate(checkout, payload, baseline_slugs)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors = [f"receipt_or_candidate_invalid:{error}"]
        payload = {}
    if errors:
        blocked = {
            "status": "BLOCKED",
            "published": False,
            "slug": payload.get("slug"),
            "canonical_url": payload.get("canonical_url"),
            "reason": ",".join(errors),
            "gates": payload.get("gates", {key: False for key in ("topic", "seo", "sources", "image", "notebooklm", "html", "rss", "git", "public_http", "recrawl")}),
            "notebooklm_score": payload.get("notebooklm_score"),
            "image_sha256": payload.get("image_sha256"),
            "commit": None,
            "recrawl_task_id": None,
        }
        save_json(receipt, blocked)
        return 2
    if dry_run:
        return 0
    try:
        release_candidate(checkout, receipt, payload, now)
    except (OSError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        payload["status"] = "BLOCKED"
        payload["published"] = False
        payload["reason"] = f"release_failed:{error}"
        save_json(receipt, payload)
        return 3
    return 0


def validate_unique_image(image_url: str, image_hash: str, registry: dict[str, Any]) -> list[str]:
    rows = registry.get("items", [])
    errors: list[str] = []
    if any(row.get("image_url") == image_url for row in rows if isinstance(row, dict)):
        errors.append("image_url_reused")
    if any(row.get("image_sha256") == image_hash for row in rows if isinstance(row, dict)):
        errors.append("image_hash_reused")
    return errors


def build_review_prompt(draft: str, digest: str, sources: dict[str, Any], image_brief: dict[str, Any]) -> str:
    return """Ты проверяешь конкретный immutable-черновик для RSS Дзена. Не описывай отсутствующие данные.
Верни только JSON: reviewed_draft_sha256, verdict (APPROVE|REVISE|BLOCKED), score_0_100,
blocking_issues[], revision_instructions[], citations[]. APPROVE допустим только при score>=80,
нуле blocking issues, соответствии изображения теме, отсутствии кликбейта и нарушений правил.

DRAFT_SHA256:
{digest}

SOURCES_JSON:
{sources}

IMAGE_BRIEF_JSON:
{image_brief}

FULL_DRAFT:
{draft}
""".format(
        digest=digest,
        sources=json.dumps(sources, ensure_ascii=False, sort_keys=True),
        image_brief=json.dumps(image_brief, ensure_ascii=False, sort_keys=True),
        draft=draft,
    )


def run_notebook_review(
    prompt: str,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    result = runner(
        ["notebooklm", "ask", "-n", NOTEBOOK_ID, "--json", "--timeout", "300", prompt],
        text=True,
        capture_output=True,
        timeout=330,
    )
    if result.returncode:
        raise RuntimeError(f"NotebookLM review failed with exit {result.returncode}")
    envelope = json.loads(result.stdout)
    answer = envelope.get("answer")
    if not isinstance(answer, str):
        raise ValueError("NotebookLM response lacks answer")
    value = answer.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1].rsplit("```", 1)[0]
    review = json.loads(value)
    if not isinstance(review, dict):
        raise ValueError("NotebookLM review is not an object")
    if "citations" not in review:
        review["citations"] = envelope.get("references", [])
    return review


def dry_run(package: Path) -> dict[str, Any]:
    draft = (package / "draft-v1.md").read_text(encoding="utf-8")
    sources = json.loads((package / "sources-context.json").read_text(encoding="utf-8"))
    image_brief = json.loads((package / "image-brief.json").read_text(encoding="utf-8"))
    receipt = {
        "mode": "dry-run",
        "draft_sha256": draft_sha256(draft),
        "sources_sha256": hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
        "image_brief_sha256": hashlib.sha256(json.dumps(image_brief, sort_keys=True).encode()).hexdigest(),
        "external_actions": [],
    }
    save_json(package / "dry-run-receipt.json", receipt)
    return receipt


def prepare(root: Path, no_publish: bool = True) -> dict[str, Any]:
    packages = sorted((root / "newsroom" / "packages").glob("*/draft-v1.md"))
    if not packages:
        return {"status": "BLOCKED", "reason": "package_queue_empty", "published": False}
    package = packages[0].parent
    receipt = dry_run(package)
    return {"status": "PREPARED", "package": str(package), "published": False, "receipt": receipt}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    dry = sub.add_parser("dry-run")
    dry.add_argument("--package", type=Path, required=True)
    review_cmd = sub.add_parser("review")
    review_cmd.add_argument("--package", type=Path, required=True)
    prepare_cmd = sub.add_parser("prepare")
    prepare_cmd.add_argument("--root", type=Path, required=True)
    prepare_cmd.add_argument("--no-publish", action="store_true", required=True)
    autonomous_cmd = sub.add_parser("autonomous")
    autonomous_cmd.add_argument("--root", type=Path, required=True)
    autonomous_cmd.add_argument("--receipt", type=Path, required=True)
    autonomous_cmd.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.command == "autonomous":
        return run_autonomous(args.root.resolve(), args.receipt.resolve(), args.dry_run)

    if args.command == "prepare":
        result = prepare(args.root.resolve(), no_publish=args.no_publish)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result["status"] == "PREPARED" else 2

    package = args.package.resolve()
    if args.command == "dry-run":
        print(json.dumps(dry_run(package), ensure_ascii=False))
        return 0

    draft_paths = sorted(package.glob("draft-v*.md"))
    if not draft_paths:
        raise SystemExit("DZEN_PIPELINE: draft missing")
    draft = draft_paths[-1].read_text(encoding="utf-8")
    digest = draft_sha256(draft)
    sources = json.loads((package / "sources-context.json").read_text(encoding="utf-8"))
    image_brief = json.loads((package / "image-brief.json").read_text(encoding="utf-8"))
    prompt = build_review_prompt(draft, digest, sources, image_brief)
    try:
        review = run_notebook_review(prompt)
    except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, json.JSONDecodeError) as error:
        save_json(package / "notebooklm-review-error.json", {"status": "BLOCKED", "error": str(error)})
        return 1
    errors = validate_review(review, digest)
    review["validation_errors"] = errors
    save_json(package / f"notebooklm-review-v{len(draft_paths)}.json", review)
    print(json.dumps(review, ensure_ascii=False))
    return 1 if errors or review.get("verdict") != "APPROVE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
