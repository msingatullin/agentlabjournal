#!/usr/bin/env python3
"""Compile measured Wordstat evidence into a reviewable SEO keyword universe."""
from __future__ import annotations

import argparse
import json
import math
import re
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN_RE = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
STOP = {
    "ai", "ии", "llm", "как", "для", "что", "это", "и", "в", "на", "с", "по",
    "the", "a", "an", "to", "of", "agent", "агент", "агенты", "agentlab", "journal",
}


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return round(ordered[low] + (ordered[high] - ordered[low]) * (position - low))


def tokens(value: str) -> set[str]:
    return {token.casefold() for token in TOKEN_RE.findall(value) if token.casefold() not in STOP}


def similarity(left: str, right: str) -> float:
    a, b = tokens(left), tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def pages(site_root: Path, domain: str, recursive: bool) -> list[dict]:
    result = []
    paths = site_root.rglob("*.html") if recursive else site_root.glob("*.html")
    for path in sorted(paths):
        match = TITLE_RE.search(path.read_text(encoding="utf-8", errors="ignore"))
        if not match:
            continue
        title = re.sub(r"\s+", " ", unescape(match.group(1))).strip()
        result.append({
            "url": f"https://{domain}/{path.relative_to(site_root).as_posix()}",
            "title": title,
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "seo-keyword-universe.json")
    parser.add_argument("--cannibalization-output", type=Path, default=ROOT / "seo-cannibalization-report.json")
    parser.add_argument("--site-root", type=Path, default=ROOT)
    parser.add_argument("--domain", default="agentlabjournal.online")
    parser.add_argument("--recursive-pages", action="store_true")
    args = parser.parse_args()

    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    keywords: dict[str, dict] = {}
    for observation in evidence["observations"]:
        seed = observation["seed"]
        total = observation["response"].get("totalCount")
        if total is not None:
            keywords.setdefault(seed.casefold(), {
                "query": seed, "frequency_value": int(total), "observed_from": []
            })["observed_from"].append(seed)
        for row in observation["response"].get("results", []):
            query = row["phrase"].strip()
            value = int(row["count"])
            key = query.casefold()
            current = keywords.get(key)
            if current is None or value > current["frequency_value"]:
                keywords[key] = {"query": query, "frequency_value": value, "observed_from": [seed]}
            elif seed not in current["observed_from"]:
                current["observed_from"].append(seed)

    values = [row["frequency_value"] for row in keywords.values()]
    low_max = percentile(values, 0.25)
    high_min = percentile(values, 0.75)
    for row in keywords.values():
        value = row["frequency_value"]
        row["frequency_class"] = "low" if value <= low_max else "high" if value >= high_min else "medium"
    rows = sorted(keywords.values(), key=lambda row: (-row["frequency_value"], row["query"]))
    source_ref = f"raw:seo/agentlab/{args.evidence.name}"
    output = {
        "schema_version": 1,
        "project": evidence["project"],
        "source_evidence": source_ref,
        "collected_at": evidence["collected_at"],
        "measurement_period": evidence["measurement_period"],
        "region": evidence["region"]["label"],
        "classification": {
            "method": "inclusive empirical quartiles over unique measured phrases",
            "low": f"frequency_value <= {low_max}",
            "medium": f"{low_max + 1} <= frequency_value < {high_min}",
            "high": f"frequency_value >= {high_min}",
        },
        "keyword_count": len(rows),
        "keywords": rows,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    site_pages = pages(args.site_root, args.domain, args.recursive_pages)
    candidates = []
    for row in rows:
        ranked = sorted(
            ({**page, "similarity": round(similarity(row["query"], page["title"]), 4)} for page in site_pages),
            key=lambda page: (-page["similarity"], page["url"]),
        )
        matches = [page for page in ranked[:5] if page["similarity"] > 0]
        candidates.append({
            "query": row["query"],
            "frequency_value": row["frequency_value"],
            "frequency_class": row["frequency_class"],
            "status": "needs_review",
            "candidate_pages": matches,
        })
    report = {
        "schema_version": 1,
        "project": evidence["project"],
        "source_evidence": source_ref,
        "rule": "Similarity is discovery evidence only; no query is assigned to a URL automatically.",
        "pages_scanned": len(site_pages),
        "queries_scanned": len(candidates),
        "candidates": candidates,
    }
    args.cannibalization_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "keywords": len(rows),
        "pages": len(site_pages),
        "low_max": low_max,
        "high_min": high_min,
        "output": str(args.output),
        "cannibalization_output": str(args.cannibalization_output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
