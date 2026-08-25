#!/usr/bin/env python3
"""Sync Admitad affiliate programs into ALJ tools/recommendations page."""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

ROOT = Path("/root/agentlabjournal")
ENV_PATH = Path(__file__).parent / ".env"
API_BASE = "https://api.admitad.com"


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
        data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret, "scope": "advcampaigns websites"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_programs(token: str, website_id: str) -> list[dict]:
    url = f"{API_BASE}/advcampaigns/"
    headers = {"Authorization": f"Bearer {token}"}
    programs = []
    offset = 0
    limit = 50
    while True:
        resp = requests.get(url, headers=headers, params={"limit": limit, "offset": offset, "website": website_id}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        programs.extend(results)
        if len(results) < limit:
            break
        offset += limit
    return programs


def generate_deeplink(token: str, website_id: str, campaign_id: int, target_url: str) -> str | None:
    if not target_url:
        return None
    url = f"{API_BASE}/deeplink/{website_id}/advcampaign/{campaign_id}/"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(url, headers=headers, data={"ulp": target_url}, timeout=30)
    if resp.status_code != 200:
        return None
    return resp.text.strip()


def build_tools_page(programs: list[dict]) -> str:
    rows = []
    for p in programs:
        name = p.get("name", "")
        site = p.get("site_url", "")
        link = p.get("gotolink", "")
        actions = p.get("actions", [])
        rate = ""
        if actions:
            rate = actions[0].get("payment_size", "")
        rows.append(f"<tr><td>{name}</td><td><a href='{link}' rel='nofollow sponsored' target='_blank'>{site}</a></td><td>{rate}</td></tr>")

    if not rows:
        rows.append("<tr><td colspan='3'>Партнёрские программы пока на модерации. Список обновится автоматически после одобрения.</td></tr>")

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Рекомендуемые инструменты и сервисы для AI-автоматизации.">
  <title>Инструменты | Agent Lab Journal</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header"><a class="brand" href="./">Agent Lab Journal</a></header>
<main class="article">
  <h1>Инструменты</h1>
  <p>Список сервисов, которые мы используем или тестируем. Ссылки могут быть партнёрскими — вы ничего не переплачиваете, а проект получает небольшой процент.</p>
  <table class="tools-table">
    <thead><tr><th>Сервис</th><th>Сайт</th><th>Вознаграждение</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <p><a href="./">← На главную</a></p>
</main>
</body>
</html>
"""


def main() -> int:
    env = load_env()
    client_id = env.get("ADMITAD_CLIENT_ID")
    client_secret = env.get("ADMITAD_CLIENT_SECRET")
    website_id = env.get("ADMITAD_WEBSITE_ID")
    if not all([client_id, client_secret, website_id]):
        print("ERROR: ADMITAD_CLIENT_ID, ADMITAD_CLIENT_SECRET and ADMITAD_WEBSITE_ID required")
        print(f"Create {ENV_PATH} with these variables.")
        return 1

    token = get_token(client_id, client_secret)
    programs = fetch_programs(token, website_id)
    print(f"Fetched {len(programs)} active programs")

    page = build_tools_page(programs)
    (ROOT / "tools.html").write_text(page, encoding="utf-8")
    print(f"Updated {ROOT / 'tools.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
