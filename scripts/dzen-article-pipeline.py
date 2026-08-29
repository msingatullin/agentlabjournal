#!/usr/bin/env python3
"""Fail-closed state and NotebookLM review gate for Dzen RSS articles."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


NOTEBOOK_ID = "7bbafa88-a8c4-44bf-9a17-77851f87d459"
MIN_SCORE = 80
MAX_REVISIONS = 3
CODEX = "/usr/bin/codex"


def draft_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def build_autonomous_prompt(dry_run: bool) -> str:
    mode = "DRY RUN: do not push, publish, submit recrawl, or mutate external services." if dry_run else "RELEASE MODE."
    return f"""You are the autonomous Dzen RSS newsroom operator for Agent Lab Journal.
Work only inside this isolated checkout. {mode}

Produce exactly one Russian news or analytical article package, or return BLOCKED. Never ask the owner questions.
Mandatory gates, in order:
1. Select one fresh, non-duplicate topic from current primary sources. Reject advertising, announcements, lists, schedules and non-news blog material.
2. Create and validate a Wordstat query passport with measured demand, intent, canonical URL and cannibalization check. Unvalidated demand blocks release.
3. Write an evidence-based article without invented tests, quotes, dates or results. Preserve source URLs and collection dates.
4. Generate a new topic-specific unique image for this article. Never reuse an existing URL or SHA-256. Record prompt, path and hash; disclose AI use.
5. Upload the immutable full draft to NotebookLM {NOTEBOOK_ID}, wait for indexing, and request strict JSON review. Require matching SHA-256, verdict APPROVE, score_0_100 >= 80, citations and zero blocking issues. Apply no more than three revisions; otherwise BLOCKED.
6. Render HTML with title/H1 alignment, canonical, description, Article JSON-LD, datePublished, source links and the approved unique image. Update homepage-covers.json.
7. Run repository publication gates and build dzen-rss.xml. Verify RSS canonical, full text and unique enclosure URL.
8. Enforce one publication per Moscow calendar day. Missed four-hour runs never accumulate and never cause a burst.
9. In RELEASE MODE only: commit only this cycle's files, git push origin main, wait for public HTTP 200, submit the canonical URL to Yandex.Webmaster recrawl, and store its accepted response/task ID.
10. Write newsroom/dzen-autonomous-state.json and a package publication-receipt.json only from observed results.

Fail closed on any missing credential, source evidence, SEO measurement, image, NotebookLM approval, validation, push, public HTTP check, RSS check or recrawl acceptance. Do not weaken authentication, repository rules or gates. Do not expose secrets.
Return only JSON matching the supplied schema.
"""


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
    if not dry_run and not publication_slot_open(state, now):
        save_json(receipt, {"status": "SKIPPED", "reason": "daily_limit", "published": False})
        return 0
    result = subprocess.run(
        build_codex_command(checkout, receipt, dry_run),
        input=build_autonomous_prompt(dry_run),
        text=True,
        timeout=3300,
    )
    return result.returncode


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
