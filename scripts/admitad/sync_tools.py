#!/usr/bin/env python3
"""Sync Admitad affiliate programs into ALJ tools/recommendations page."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import requests
import yaml

ROOT = Path("/root/agentlabjournal")
SCRIPT_DIR = Path(__file__).parent
ENV_PATH = SCRIPT_DIR / ".env"
CONFIG_PATH = SCRIPT_DIR / "tools.yaml"
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


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def get_token(client_id: str, client_secret: str, scope: str) -> str:
    resp = requests.post(
        f"{API_BASE}/token/",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_ad_space_programs(token: str, website_id: str, connection_status: str) -> list[dict]:
    url = f"{API_BASE}/advcampaigns/website/{website_id}/"
    headers = {"Authorization": f"Bearer {token}"}
    programs = []
    offset = 0
    limit = 50
    while True:
        resp = requests.get(
            url,
            headers=headers,
            params={"limit": limit, "offset": offset, "connection_status": connection_status},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        programs.extend(results)
        if len(results) < limit:
            break
        offset += limit
    return programs


def generate_deeplink(token: str, website_id: str, campaign_id: int, target_url: str, subid: str = "alj_tools") -> str | None:
    if not target_url:
        return None
    url = f"{API_BASE}/deeplink/{website_id}/advcampaign/{campaign_id}/"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"ulp": target_url}
    if subid:
        params["subid"] = subid
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"WARN: deeplink failed for campaign {campaign_id}: {resp.status_code} {resp.text[:200]}")
        return None
    try:
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0].get("link")
        return None
    except Exception as exc:
        print(f"WARN: deeplink parse failed for campaign {campaign_id}: {exc}")
        return None


def find_target_config(config: dict, program_name: str) -> dict | None:
    name_lower = program_name.lower()
    for target in config.get("targets", []):
        for search_name in target.get("search_names", []):
            if search_name.lower() in name_lower:
                return target
    return None


def fetch_stats(token: str, website_id: str, date_start: str, date_end: str) -> dict:
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
    return resp.json()


def build_tools_page(programs: list[dict]) -> str:
    rows = []
    for p in programs:
        name = p.get("name", "").replace("<", "&lt;").replace(">", "&gt;")
        site = p.get("site_url", "")
        link = p.get("deeplink") or p.get("gotolink", "")
        description = p.get("description", "").replace("<", "&lt;").replace(">", "&gt;")
        actions = p.get("actions", [])
        rate = ""
        if actions:
            rate = actions[0].get("payment_size", "")
        rows.append(
            f"<tr><td>{name}</td><td>{description}</td>"
            f"<td><a href='{link}' rel='nofollow sponsored' target='_blank'>{site}</a></td><td>{rate}</td></tr>"
        )

    if not rows:
        rows.append(
            "<tr><td colspan='4'>Партнёрские программы пока на модерации. "
            "Список обновится автоматически после одобрения.</td></tr>"
        )

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Рекомендуемые инструменты и сервисы для AI-автоматизации.">
  <title>Рекомендуем | Agent Lab Journal</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header"><a class="brand" href="./">Agent Lab Journal</a></header>
<main class="article">
  <h1>Рекомендуем</h1>
  <p>Список сервисов, которые мы используем или тестируем. Ссылки могут быть партнёрскими — вы ничего не переплачиваете, а проект получает небольшой процент.</p>
  <table class="tools-table">
    <thead><tr><th>Сервис</th><th>Описание</th><th>Сайт</th><th>Вознаграждение</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <p><a href="./">← На главную</a></p>
</main>
</body>
</html>
"""


def write_stats(token: str, website_id: str) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    first_day = datetime.now().replace(day=1).strftime("%d.%m.%Y")
    today_fmt = datetime.now().strftime("%d.%m.%Y")
    stats = fetch_stats(token, website_id, first_day, today_fmt)
    stats_path = ROOT / "scripts" / "admitad" / f"stats-{today}.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return stats_path


def main() -> int:
    env = load_env()
    client_id = env.get("ADMITAD_CLIENT_ID")
    client_secret = env.get("ADMITAD_CLIENT_SECRET")
    website_id = env.get("ADMITAD_WEBSITE_ID")
    if not all([client_id, client_secret, website_id]):
        print("ERROR: ADMITAD_CLIENT_ID, ADMITAD_CLIENT_SECRET and ADMITAD_WEBSITE_ID required")
        print(f"Create {ENV_PATH} with these variables.")
        return 1

    config = load_config()
    token = get_token(client_id, client_secret, "advcampaigns_for_website websites deeplink_generator statistics")

    active_programs = fetch_ad_space_programs(token, website_id, "active")
    pending_programs = fetch_ad_space_programs(token, website_id, "pending")
    declined_programs = fetch_ad_space_programs(token, website_id, "declined")

    print(f"Active programs: {len(active_programs)}")
    print(f"Pending programs: {len(pending_programs)}")
    print(f"Declined programs: {len(declined_programs)}")

    for p in active_programs:
        target = find_target_config(config, p.get("name", ""))
        target_url = target.get("landing_url", "") if target else config.get("default_landing_url", "")
        if not target_url:
            target_url = p.get("site_url", "")
        if target_url and p.get("allow_deeplink"):
            deeplink = generate_deeplink(token, website_id, p["id"], target_url)
            if deeplink:
                p["deeplink"] = deeplink
                print(f"Generated deeplink for {p['name']}: {deeplink[:80]}...")

    page = build_tools_page(active_programs)
    (ROOT / "tools.html").write_text(page, encoding="utf-8")
    print(f"Updated {ROOT / 'tools.html'}")

    try:
        stats_path = write_stats(token, website_id)
        print(f"Saved stats to {stats_path}")
    except Exception as exc:
        print(f"WARN: could not save stats: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
