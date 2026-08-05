# AgentLab lead API contract

Canonical payload: [`api-schema-v1.2.json`](./api-schema-v1.2.json).

- Endpoint: `POST https://api.grifun.ru/api/leads` (v1.2, when enabled).
- Legacy fallback must preserve the full v1.2 payload locally and place metadata in the legacy comment field; it must not silently discard UTM or article attribution.
- Success gate: HTTP 2xx, parseable JSON response, local evidence record, redirect to `/thanks.html`.
- Failure gate: record status/error without credentials or personal tokens; show the Telegram fallback to the owner.

Smoke test uses a synthetic contact only. Never use a real customer record in a test:

```bash
python3 /root/scripts/evaluate-lead-intake.py
```

The API schema is a contract, not proof that the remote endpoint accepts it. Acceptance requires a real response artifact from the current endpoint.
