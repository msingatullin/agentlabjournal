#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=/root/agentlabjournal
DRY_RUN_RECEIPTS_REQUIRED=2
SERVICE=agentlab-dzen-article-pipeline.service
TIMER=agentlab-dzen-article-pipeline.timer

systemd-analyze verify "$PROJECT_ROOT/ops/systemd/$SERVICE" "$PROJECT_ROOT/ops/systemd/$TIMER"

receipt_count=$(find /var/lib/agentlab-dzen -maxdepth 1 -name 'dry-run-*.json' -type f -exec grep -l '"status": "PREPARED"\|"status":"PREPARED"' {} \; 2>/dev/null | wc -l)
if [ "$receipt_count" -lt "$DRY_RUN_RECEIPTS_REQUIRED" ]; then
  echo "DZEN_TIMER_MIGRATION: BLOCKED dry-run receipts=$receipt_count required=$DRY_RUN_RECEIPTS_REQUIRED" >&2
  exit 2
fi

install -m 0644 "$PROJECT_ROOT/ops/systemd/$SERVICE" "/etc/systemd/system/$SERVICE"
install -m 0644 "$PROJECT_ROOT/ops/systemd/$TIMER" "/etc/systemd/system/$TIMER"
systemctl daemon-reload
systemctl disable --now hermes-dzen-send.timer
systemctl enable --now "$TIMER"
systemctl is-enabled "$TIMER"
systemctl is-active "$TIMER"
