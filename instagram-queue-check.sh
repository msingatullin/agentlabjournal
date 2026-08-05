#!/usr/bin/env bash
set -euo pipefail

QUEUE="${1:-/root/wiki/system/instagram-post-queue.json}"
MIN_DAYS="${MIN_INSTAGRAM_QUEUE_DAYS:-7}"
if [[ ! -f "$QUEUE" ]]; then
  echo "INSTAGRAM_QUEUE: MISSING $QUEUE" >&2
  exit 2
fi

count=$(python3 - "$QUEUE" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    data=json.load(f)
items=data if isinstance(data,list) else data.get('items', data.get('posts', data.get('queue', [])))
print(len(items))
PY
)
required=$((MIN_DAYS * 2))
if (( count < required )); then
  echo "INSTAGRAM_QUEUE: LOW count=$count required=$required" >&2
  echo "NOTIFY_REQUIRED=telegram_or_email" >&2
fi
python3 /root/scripts/instagram-queue-audit.py --queue "$QUEUE" --min-days "$MIN_DAYS" >/tmp/agentlab-instagram-queue-audit.json || true
if ! grep -q '"status": "OK"' /tmp/agentlab-instagram-queue-audit.json; then
  echo "INSTAGRAM_QUEUE: PROVENANCE_AUDIT=PARTIAL" >&2
  cat /tmp/agentlab-instagram-queue-audit.json >&2
  exit 1
fi
if (( count < required )); then
  exit 1
fi
echo "INSTAGRAM_QUEUE: OK count=$count required=$required provenance=OK"
