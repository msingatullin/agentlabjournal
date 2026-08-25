#!/usr/bin/env python3
"""Generate a weekly Admitad CPA report for ALJ."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
ENV_PATH = SCRIPT_DIR / ".env"
API_BASE = "https://api.admitad.com"
WIKI_DIR = Path("/root/wiki/finance")


def load_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("ADMITAD_")})
    return env


def get_token(client_id: str, client_secret: str) -> str:
    resp = requests.post(
        f"{API_BASE}/token/",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "statistics",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_website_stats(token: str, website_id: str, date_start: str, date_end: str) -> dict:
    url = f"{API_BASE}/statistics/websites/"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "website": website_id,
        "date_start": date_start,
        "date_end": date_end,
        "limit": 1,
        "total": 1,
    }
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list) and data:
        return data[0]
    return data.get("results", [{}])[0] if isinstance(data, dict) else {}


def fetch_campaign_stats(token: str, website_id: str, date_start: str, date_end: str) -> list[dict]:
    url = f"{API_BASE}/statistics/campaigns/"
    headers = {"Authorization": f"Bearer {token}"}
    results = []
    offset = 0
    limit = 50
    while True:
        params = {
            "website": website_id,
            "date_start": date_start,
            "date_end": date_end,
            "limit": limit,
            "offset": offset,
            "total": 0,
        }
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        page = data.get("results", [])
        results.extend(page)
        if len(page) < limit:
            break
        offset += limit
    return results


def build_report(website_id: str, period_start: str, period_end: str, website_stats: dict, campaign_stats: list[dict]) -> str:
    lines = [
        f"# Admitad CPA report: {period_start} — {period_end}",
        "",
        f"- Ad space ID: `{website_id}`",
        f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Total by ad space",
        "",
        "| Clicks | Views | Leads | Sales | Approved | Open | Declined |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        f"| {website_stats.get('clicks', 0)} | {website_stats.get('views', 0)} | "
        f"{website_stats.get('leads_sum', 0)} | {website_stats.get('sales_sum', 0)} | "
        f"{website_stats.get('payment_sum_approved', 0)} | {website_stats.get('payment_sum_open', 0)} | "
        f"{website_stats.get('payment_sum_declined', 0)} |",
        "",
        "## By campaign",
        "",
        "| Campaign | Clicks | Leads | Sales | Approved | Open |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c in campaign_stats:
        lines.append(
            f"| {c.get('advcampaign_name', '')} | {c.get('clicks', 0)} | "
            f"{c.get('leads_sum', 0)} | {c.get('sales_sum', 0)} | "
            f"{c.get('payment_sum_approved', 0)} | {c.get('payment_sum_open', 0)} |"
        )
    if not campaign_stats:
        lines.append("| — | — | — | — | — | — |")
    lines.extend(["", "---", "Source: Admitad API `/statistics/websites/` and `/statistics/campaigns/`."])
    return "\n".join(lines) + "\n"


def main() -> int:
    env = load_env()
    client_id = env.get("ADMITAD_CLIENT_ID")
    client_secret = env.get("ADMITAD_CLIENT_SECRET")
    website_id = env.get("ADMITAD_WEBSITE_ID")
    if not all([client_id, client_secret, website_id]):
        print("ERROR: ADMITAD_CLIENT_ID, ADMITAD_CLIENT_SECRET and ADMITAD_WEBSITE_ID required")
        return 1

    end = datetime.now()
    start = end - timedelta(days=7)
    date_start = start.strftime("%d.%m.%Y")
    date_end = end.strftime("%d.%m.%Y")
    period_start = start.strftime("%Y-%m-%d")
    period_end = end.strftime("%Y-%m-%d")

    token = get_token(client_id, client_secret)
    website_stats = fetch_website_stats(token, website_id, date_start, date_end)
    campaign_stats = fetch_campaign_stats(token, website_id, date_start, date_end)

    report = build_report(website_id, period_start, period_end, website_stats, campaign_stats)

    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    report_path = WIKI_DIR / f"admitad-weekly-{period_end}.md"
    report_path.write_text(report, encoding="utf-8")

    latest_path = WIKI_DIR / "admitad-latest.md"
    latest_path.write_text(report, encoding="utf-8")

    print(f"Saved report to {report_path} and {latest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
