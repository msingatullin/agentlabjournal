#!/usr/bin/env python3
"""Research agent: build a dated candidate package from recent primary sources."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

from podcast_contract import HOSTS, INTRO_EXACT, OUTRO_EXACT, expected_rubric, write_json

ROOT = Path("/root")
PROJECT = Path("/root/agentlabjournal")
NOTEBOOK = "3a91cab6-c483-4a8c-aadf-24afb78d8d8a"
NOTEBOOKLM = "/root/scripts/notebooklm-via-gcp"
PRIMARY_DOMAINS = {
    "news.microsoft.com", "blogs.microsoft.com", "microsoft.com", "www.microsoft.com",
    "blogs.nvidia.com", "nvidia.com", "www.nvidia.com",
    "github.blog", "github.com",
    "nist.gov", "www.nist.gov",
    "digital-strategy.ec.europa.eu", "ec.europa.eu", "europa.eu",
    "duma.gov.ru", "www.duma.gov.ru",
    "aws.amazon.com", "amazon.com", "www.amazon.com",
    "arxiv.org", "www.frontiersin.org",
    "openai.com", "www.openai.com",
    "anthropic.com", "www.anthropic.com",
    "deepmind.google", "blog.google", "ai.google", "research.google", "googleblog.com",
    "ai.meta.com", "meta.ai", "about.fb.com", "meta.com",
    "mistral.ai", "www.mistral.ai",
    "x.ai", "www.x.ai",
    "stability.ai", "www.stability.ai",
    "cohere.com", "www.cohere.com",
    "apple.com", "www.apple.com",
    "sec.gov", "www.sec.gov",
    "cisa.gov", "www.cisa.gov",
    "whitehouse.gov", "www.whitehouse.gov",
    "gov.uk", "www.gov.uk",
    "ftc.gov", "www.ftc.gov",
}


def run(command: list[str], timeout: int = 300) -> str:
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"COMMAND_TIMEOUT: {timeout}s: {' '.join(command[:4])}") from error
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-4000:])
    return result.stdout


def import_research(command: list[str]) -> str:
    """Full research only: retry transient NotebookLM failures, never --no-research."""
    errors = []
    for attempt, timeout in enumerate((120, 300, 300), start=1):
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
            if result.returncode == 0:
                return result.stdout
            errors.append((result.stderr or result.stdout)[-3000:])
        except subprocess.TimeoutExpired:
            errors.append(f"attempt {attempt}: timeout after {timeout}s")
        if attempt < 3:
            time.sleep(5)
    raise RuntimeError("RESEARCH_IMPORT_RETRIES_EXHAUSTED: " + " | ".join(errors)[-4000:])


def extract_object(payload: dict) -> dict:
    answer = payload.get("answer", "")
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", answer, re.S)
    return json.loads(match.group(1) if match else answer.strip())


def source_date(content: str, url: str, allowed_dates: list[dt.date]) -> tuple[dt.date | None, str | None]:
    """Return only a publication/update date evidenced by primary source text."""
    for value in sorted(allowed_dates, reverse=True):
        month = value.strftime("%B")
        patterns = (
            rf"\b{re.escape(month)}\s+{value.day},\s+{value.year}\b",
            rf"\b{value.day}\s+{re.escape(month)}\s+{value.year}\b",
            rf"\b{value.isoformat()}\b",
            rf"\b{value.month:02d}/{value.day:02d}/{value.year}\b",
        )
        if any(re.search(pattern, content, re.I) for pattern in patterns):
            return value, "source_text"
    return None, None


def exact_evidence_terms(content: str, claim: str, title: str, limit: int = 3) -> list[str]:
    """Select exact, claim-relevant source excerpts without asking an LLM to quote."""
    claim_tokens = {
        token for token in re.findall(r"[a-zа-яё0-9]+", claim.casefold())
        if len(token) >= 4
    }
    chunks = [re.sub(r"\s+", " ", chunk).strip() for chunk in re.split(r"(?<=[.!?])\s+|\n+", content)]
    title_value = re.sub(r"\s+", " ", title).strip().casefold()
    ranked = sorted(
        (
            chunk for chunk in chunks
            if 60 <= len(chunk) <= 600
            and not chunk.casefold().startswith(("http://", "https://"))
            and chunk.casefold() != title_value
            and chunk.casefold() not in title_value
        ),
        key=lambda chunk: (-len(claim_tokens & set(re.findall(r"[a-zа-яё0-9]+", chunk.casefold()))), len(chunk)),
    )
    result = []
    for chunk in ranked:
        excerpt = " ".join(chunk.split()[:24]).strip()
        if excerpt and excerpt not in result:
            result.append(excerpt)
        if len(result) == limit:
            break
    return result


def select_news(notebook: str, catalog: str, target: dt.date, evidence_by_id: dict[str, str], window_days: int = 3) -> dict:
    allowed_dates = {(target - dt.timedelta(days=offset)).isoformat() for offset in range(window_days)}
    rejected_ids: set[str] = set()
    last_error = "no selection attempted"
    for attempt in range(1, 4):
        prompt = f"""Ты Research Agent. Выбери 2-3 новости, опубликованные или официально обновлённые строго в одну из дат {sorted(allowed_dates)}, только из каталога ниже.
Верни только JSON с ключами news, daily_topic, listener_takeaway.
Каждая news: title, date YYYY-MM-DD, source_id, source_url, claim, why_it_matters, evidence_terms (3-4 точные строки из источника), qa_terms (3 коротких термина для транскрипта).
evidence_terms сохраняй дословно на языке первичного источника. qa_terms обязательно формулируй только кириллицей по-русски именно так, как ведущие должны произнести их в русскоязычном выпуске. Латиница, английские пояснения и скобки в qa_terms запрещены. Не копируй английские evidence_terms в qa_terms.
Поле date обязано дословно совпадать с published_date из каталога. Источники уже прошли детерминированную проверку даты.
Не изменяй source_id/source_url. Не добавляй источники вне каталога. Не называй исследование одной компании универсальной статистикой.
Не выбирай source_id из списка отклонённых: {sorted(rejected_ids)}.
Каталог: {catalog}
"""
        ask_timeout = 120 if attempt == 1 else 300
        try:
            answer = json.loads(run(
                [NOTEBOOKLM, "ask", "--notebook", notebook, "--new", "--yes", "--json", prompt],
                timeout=ask_timeout,
            ))
        except (RuntimeError, json.JSONDecodeError) as error:
            last_error = f"attempt {attempt}: {error}"
            continue
        selected = extract_object(answer)
        news = selected.get("news", [])
        for item in news:
            item["evidence_terms"] = exact_evidence_terms(
                evidence_by_id.get(item.get("source_id", ""), ""),
                str(item.get("claim", "")),
                str(item.get("title", "")),
            )
        invalid = [item for item in news if item.get("date") not in allowed_dates]
        invalid_qa = [
            item for item in news
            if not item.get("qa_terms")
            or any(re.search(r"[a-z]", str(term), re.I) for term in item["qa_terms"])
        ]
        unsupported = []
        for item in news:
            content = re.sub(r"\s+", " ", evidence_by_id.get(item.get("source_id", ""), "").casefold()).strip()
            terms = item.get("evidence_terms") or []
            if not terms or any(re.sub(r"\s+", " ", term.casefold()).strip() not in content for term in terms):
                unsupported.append(item)
        if len(news) >= 2 and not invalid and not invalid_qa and not unsupported:
            return selected
        rejected_ids.update(item.get("source_id", "") for item in invalid + unsupported)
        last_error = f"attempt {attempt}: {len(news)} news, invalid dates={[(x.get('source_id'), x.get('date')) for x in invalid]}, invalid_qa={[x.get('source_id') for x in invalid_qa]}, unsupported={[x.get('source_id') for x in unsupported]}"
    raise RuntimeError(f"RESEARCH_DATE_GATE: unable to select two current items; {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--notebook", default=NOTEBOOK)
    parser.add_argument("--no-research", action="store_true")
    args = parser.parse_args()
    if not args.no_research:
        query = (
            f"Проверяемые AI/IT новости за предыдущие 7 дней к {args.date}. "
            "Только официальные блоги компаний, регуляторы и первичные документы; без агрегаторов и пересказов."
        )
        research_error = None
        try:
            import_research([NOTEBOOKLM, "source", "add-research", query, "--mode", "fast", "--notebook", args.notebook, "--import-all"])
        except RuntimeError as error:
            research_error = str(error)
    else:
        research_error = None
    try:
        sources = json.loads(run([NOTEBOOKLM, "source", "list", "--notebook", args.notebook, "--json"]))
    except (RuntimeError, json.JSONDecodeError) as error:
        output = PROJECT / "podcasts/packages" / f"{args.date}-ru.candidate.json"
        print(f"NOTEBOOKLM_UNAVAILABLE: using direct fallback: {str(error)[-500:]}")
        subprocess.run([
            "python3", str(PROJECT / "scripts" / "podcast_direct_fallback.py"),
            "--date", args.date, "--output", str(output),
        ], check=True)
        return 0
    target = dt.date.fromisoformat(args.date)
    maximum_window_days = 7
    allowed_date_values = [target - dt.timedelta(days=offset) for offset in range(maximum_window_days)]
    eligible = []
    for source in sources.get("sources", []):
        host = urlparse(source.get("url") or "").hostname
        title = source.get("title") or ""
        topic_match = re.search(r"\b(AI|ИИ|LLM|language model|ChatGPT|Copilot|algorithm|neural|multimodal|agent|робот|quantum)\b", title, re.I)
        if source.get("status") == "ready" and host in PRIMARY_DOMAINS and topic_match:
            item = {key: source.get(key) for key in ("id", "title", "url", "created_at")}
            try:
                fulltext = json.loads(run([NOTEBOOKLM, "source", "fulltext", item["id"], "--notebook", args.notebook, "--json"], timeout=60))
                published, evidence = source_date(fulltext.get("content") or "", item["url"], allowed_date_values)
            except (RuntimeError, json.JSONDecodeError):
                published, evidence = None, None
            if published:
                item.update({"published_date": published.isoformat(), "date_evidence": evidence, "_content": fulltext.get("content") or ""})
                eligible.append(item)
    window_days = next(
        (days for days in (2, 3, 7) if sum(
            dt.date.fromisoformat(item["published_date"]) >= target - dt.timedelta(days=days - 1)
            for item in eligible
        ) >= 2),
        None,
    )
    if window_days is None:
        detail = f"; import_error={research_error}" if research_error else ""
        raise RuntimeError("RESEARCH_GATE: fewer than two primary sources with evidenced dates in seven days" + detail)
    eligible = [
        item for item in eligible
        if dt.date.fromisoformat(item["published_date"]) >= target - dt.timedelta(days=window_days - 1)
    ]
    unique = {}
    for item in eligible:
        unique[item["url"]] = item
    focused = [
        item for item in unique.values()
        if re.search(r"\b(AI|LLM|language model|ChatGPT|algorithmic|neural|multimodal)\b", item["title"] or "", re.I)
    ]
    chosen_catalog = (focused or list(unique.values()))[-10:]
    evidence_by_id = {item["id"]: item.pop("_content", "") for item in chosen_catalog}
    catalog = json.dumps(chosen_catalog, ensure_ascii=False)
    selected = select_news(args.notebook, catalog, target, evidence_by_id, window_days)
    package = {
        "date": args.date, "language": "ru", "rubric": expected_rubric(args.date),
        "hosts": HOSTS, "intro_exact": INTRO_EXACT, "news": selected.get("news", []),
        "news_window_days": window_days,
        "news_window_label": {2: "Новости за последние 24 часа", 3: "Новости за последние 72 часа", 7: "Новости за последние 7 дней"}[window_days],
        "daily_topic": selected.get("daily_topic"), "listener_takeaway": selected.get("listener_takeaway"),
        "outro_exact": OUTRO_EXACT,
    }
    output = PROJECT / "podcasts/packages" / f"{args.date}-ru.candidate.json"
    write_json(output, package)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
