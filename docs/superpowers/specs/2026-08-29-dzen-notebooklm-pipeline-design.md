# Dzen NotebookLM Publication Pipeline Design

The pipeline prepares material every four hours and publishes no more than one
NotebookLM-approved article per Moscow calendar day. It is fail-closed: missing
SEO demand, sources, a unique topic-specific image, deterministic checks,
NotebookLM approval, deploy verification, or Yandex recrawl evidence blocks
release. Review uses notebook `7bbafa88-a8c4-44bf-9a17-77851f87d459`, the full
immutable draft and image brief, a matching SHA-256, JSON validation, score
`>=80`, no blocking issues and at most three revision attempts.

Each package under `newsroom/packages/<id>/` stores topic/source manifests,
draft revisions, image brief and asset metadata, precheck reports, NotebookLM
verdicts, state and publication receipt. Shared/recolored/reused images are
forbidden by URL and content hash. RSS/HTML metadata must reference the same
asset. Missed slots expire and are never published as a catch-up burst.

The new timer is installed disabled. After two non-publishing dry-runs prove
normal and idempotent behavior, `hermes-dzen-send.timer` is disabled/stopped and
the new timer is enabled. Public release remains separately gated.
