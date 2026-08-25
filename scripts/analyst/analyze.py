#!/usr/bin/env python3
"""Universal Analyst Agent — weekly project/finance/outreach report."""
from __future__ import annotations

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/root")
WIKI = ROOT / "wiki"
REPORT_DIR = WIKI / "agents" / "analyst" / "reports"
FINANCE_SNAPSHOT = WIKI / "finance" / "finance-chief-snapshot.json"
MMW_CRM = ROOT / "mmw" / "docs" / "fundraising" / "fundraising-crm.md"
TASKS_INDEX = WIKI / "tasks" / "index.md"
PODCAST_RSS = ROOT / "agentlabjournal" / "podcast-rss.xml"
IGNORE_DIRS = {".venv", "venv", "node_modules", ".git", "__pycache__", ".gradle", ".kotlin", ".android", ".cache", ".npm", ".local", ".config", ".vscode-server", ".superpowers", "out", "raw", "media", "assets", "android-download"}


def find_git_repos() -> list[Path]:
    repos = []
    for git_dir in ROOT.rglob(".git"):
        # ignore .git dirs inside blacklisted parent directories; keep the .git itself
        if any(part in IGNORE_DIRS for part in git_dir.parent.parts):
            continue
        repo = git_dir.parent
        if (repo / ".git" / "HEAD").exists():
            repos.append(repo)
    return sorted(set(repos))


def git_activity(repo: Path, days: int = 7) -> dict:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        log = subprocess.run(
            ["git", "log", f"--since={since}", "--pretty=format:%ad|%s", "--date=short", "--"],
            cwd=repo, text=True, capture_output=True, check=True, timeout=30,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return {"commits": 0, "days": 0, "subjects": []}
    lines = [line for line in log.splitlines() if line.strip()]
    days_set = {line.split("|")[0] for line in lines if "|" in line}
    subjects = [line.split("|", 1)[1] for line in lines if "|" in line]
    return {"commits": len(lines), "days": len(days_set), "subjects": subjects[:10]}


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def parse_outreach_crm() -> dict:
    text = MMW_CRM.read_text(encoding="utf-8") if MMW_CRM.exists() else ""
    sent = len(re.findall(r"\|\s*Sent", text, re.I))
    ready = len(re.findall(r"\|\s*Ready to send", text, re.I))
    rejected = len(re.findall(r"\|\s*Rejected", text, re.I))
    not_sent = len(re.findall(r"\|\s*Not sent", text, re.I))
    return {"sent": sent, "ready": ready, "rejected": rejected, "not_sent": not_sent}


def count_task_statuses() -> dict:
    text = TASKS_INDEX.read_text(encoding="utf-8") if TASKS_INDEX.exists() else ""
    statuses = ["inbox", "open", "waiting", "done", "canceled"]
    return {s: len(re.findall(rf"\|\s*{s}\s*\|", text, re.I)) for s in statuses}


def latest_podcast_date() -> str | None:
    if not PODCAST_RSS.exists():
        return None
    try:
        root = ET.parse(PODCAST_RSS).getroot()
        latest = None
        for item in root.findall("./channel/item"):
            pub = item.findtext("pubDate")
            if pub:
                try:
                    d = datetime.strptime(pub, "%a, %d %b %Y %H:%M:%S %z").date()
                except ValueError:
                    continue
                if latest is None or d > latest:
                    latest = d
        return latest.isoformat() if latest else None
    except Exception:
        return None


def project_name(repo: Path) -> str:
    return repo.name or str(repo)


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    report_path = REPORT_DIR / f"{today}.md"

    repos = find_git_repos()
    repo_activity = {project_name(r): git_activity(r) for r in repos}
    active_projects = {k: v for k, v in repo_activity.items() if v["commits"] > 0}
    sorted_projects = sorted(active_projects.items(), key=lambda x: x[1]["commits"], reverse=True)

    finance = load_json(FINANCE_SNAPSHOT)
    balances = finance.get("confirmed_balances", {})
    total_balance = sum(float(b.get("amount", 0)) for b in balances.values())
    cash_gap = finance.get("cash_gap_status", "unknown")

    outreach = parse_outreach_crm()
    tasks = count_task_statuses()
    podcast_latest = latest_podcast_date()

    lines = [
        f"# Аналитический отчёт — {today}",
        "",
        "> Сгенерировано агентом-аналитиком. Источники: git-логи, finance snapshot, fundraising CRM, tasks, podcast RSS.",
        "",
        "## Краткий вывод",
        "",
    ]

    if not active_projects:
        lines.append("За последние 7 дней активность в git-репозиториях не обнаружена.")
    else:
        total_commits = sum(v["commits"] for v in active_projects.values())
        lines.append(f"За последние 7 дней: **{total_commits} коммитов** в **{len(active_projects)} проектах**. "
                     "Самый активный проект — ключ к пониманию, куда уходят силы.")
    lines.append("")
    lines.append(f"**Кэш:** всего подтверждённых остатков **{total_balance:.2f} RUB**, статус gap — **{cash_gap}**.")
    lines.append(f"**Последний подкаст:** {podcast_latest or 'не опубликован'}.")
    lines.append("")

    lines.append("## Распределение времени (по git-активности)")
    lines.append("")
    lines.append("| Проект | Коммитов | Активных дней | Последние темы |")
    lines.append("|--------|----------|---------------|----------------|")
    for name, data in sorted_projects[:10]:
        subjects = "; ".join(data["subjects"][:3]) or "—"
        lines.append(f"| {name} | {data['commits']} | {data['days']} | {subjects} |")
    lines.append("")

    lines.append("## Деньги и конверсия")
    lines.append("")
    lines.append("### Балансы")
    for agent, bal in balances.items():
        lines.append(f"- **{agent}:** {bal.get('amount', '?')} {bal.get('currency', 'RUB')}")
    lines.append("")
    lines.append("### Outreach (MMW)")
    lines.append(f"- Отправлено инвесторских писем: **{outreach['sent']}**")
    lines.append(f"- Готово к отправке: **{outreach['ready']}**")
    lines.append(f"- Отказов: **{outreach['rejected']}**")
    lines.append(f"- Не отправлено: **{outreach['not_sent']}**")
    lines.append("")
    lines.append("### Задачи")
    lines.append(f"- Открыто/в работе: **{tasks.get('open', 0) + tasks.get('inbox', 0)}**")
    lines.append(f"- Ожидают: **{tasks.get('waiting', 0)}**")
    lines.append(f"- Выполнено: **{tasks.get('done', 0)}**")
    lines.append("")

    lines.append("## Красные флаги")
    lines.append("")
    red_flags = []
    if cash_gap == "gap":
        red_flags.append("**Кэш-разрыв:** подтверждённых остатков недостаточно. Доходная работа критична.")
    if outreach["sent"] == 0 and outreach["ready"] == 0:
        red_flags.append("**Outreach заморожен:** нет активных писем ни в работе, ни готовых к отправке.")
    if not podcast_latest or (datetime.now().date() - date.fromisoformat(podcast_latest)).days > 3:
        red_flags.append(f"**Подкасты отстают:** последний выпуск {podcast_latest or 'не найден'}.")
    if len(active_projects) > 5:
        red_flags.append(f"**Распыление:** активность в {len(active_projects)} проектах одновременно. Конверсия падает.")
    if not red_flags:
        red_flags.append("Критических флагов не выявлено, но дохода пока нет.")
    for flag in red_flags:
        lines.append(f"- {flag}")
    lines.append("")

    lines.append("## Рекомендации (топ-3)")
    lines.append("")
    recommendations = [
        "**Доход сначала.** Из всех текущих проектов выбрать один, который может дать деньги в течение 7 дней: активный клиентский запрос, готовая услуга, подписчик с намерением. Всё остальное — в фон.",
        "**Outreach с корпоративной почтой.** Как только DNS/PTR заработают, отправить 5 писем дизайн-партнёрам и 6 инвесторам. Это измеримая активность, которая может дать отклик.",
        "**Подкаст = тёплый трафик.** Восстановить ежедневные выпуски. Каждый выпуск — повод для поста в Telegram/LinkedIn и новый вход на сайт, где можно предложить услуги.",
    ]
    for i, rec in enumerate(recommendations, 1):
        lines.append(f"{i}. {rec}")
    lines.append("")

    lines.append("## Метрики для отслеживания")
    lines.append("")
    lines.append("- Доход от ИИ-проектов за неделю: **0 RUB** (нужно >= целевой сумме).")
    lines.append(f"- Новых инвесторских/партнёрских ответов: **{outreach['sent']} отправлено, 0 ответов**.")
    lines.append(f"- Активных проектов по git: **{len(active_projects)}**.")
    lines.append("")

    lines.append("---")
    lines.append("Агент-аналитик запускается командой: `/root/agentlabjournal/scripts/analyst/analyze.py`")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
