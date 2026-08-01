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
    parser.add_argument("evidence", type=Path, nargs="+")
    parser.add_argument("--project")
    parser.add_argument("--output", type=Path, default=ROOT / "seo-keyword-universe.json")
    parser.add_argument("--cannibalization-output", type=Path, default=ROOT / "seo-cannibalization-report.json")
    parser.add_argument("--site-root", type=Path, default=ROOT)
    parser.add_argument("--domain", default="agentlabjournal.online")
    parser.add_argument("--recursive-pages", action="store_true")
    args = parser.parse_args()

    evidence_sets = [json.loads(path.read_text(encoding="utf-8")) for path in args.evidence]
    evidence = evidence_sets[0]
    if any(item["region"]["label"] != evidence["region"]["label"] for item in evidence_sets):
        raise SystemExit("all evidence snapshots must use the same region")
    keywords: dict[str, dict] = {}
    cluster_counts: dict[str, dict[str, int]] = {}
    for observation in (row for item in evidence_sets for row in item["observations"]):
        seed = observation["seed"]
        cluster = cluster_counts.setdefault(seed, {})
        total = observation["response"].get("totalCount")
        if total is not None:
            cluster[seed.casefold()] = int(total)
            keywords.setdefault(seed.casefold(), {
                "query": seed, "frequency_value": int(total), "observed_from": []
            })["observed_from"].append(seed)
        for row in observation["response"].get("results", []):
            query = row["phrase"].strip()
            value = int(row["count"])
            key = query.casefold()
            cluster[key] = max(cluster.get(key, 0), value)
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
        row["cluster_frequency_classes"] = []
        key = row["query"].casefold()
        for seed in row["observed_from"]:
            counts = cluster_counts.get(seed, {})
            if key not in counts or not counts:
                continue
            cluster_values = list(counts.values())
            cluster_low = percentile(cluster_values, 0.25)
            cluster_high = percentile(cluster_values, 0.75)
            cluster_value = counts[key]
            cluster_class = (
                "insufficient_distribution" if len(cluster_values) < 4
                else "low" if cluster_value <= cluster_low
                else "high" if cluster_value >= cluster_high
                else "medium"
            )
            row["cluster_frequency_classes"].append({
                "seed": seed,
                "frequency_class": cluster_class,
                "low_max": cluster_low,
                "high_min": cluster_high,
            })
    rows = sorted(keywords.values(), key=lambda row: (-row["frequency_value"], row["query"]))
    source_refs = [
        "raw:" + str(path).removeprefix("/root/raw/") if str(path).startswith("/root/raw/") else str(path)
        for path in args.evidence
    ]
    source_ref: str | list[str] = source_refs[0] if len(source_refs) == 1 else source_refs
    output = {
        "schema_version": 1,
        "project": args.project or evidence["project"],
        "source_evidence": source_ref,
        "collected_at": max(item["collected_at"] for item in evidence_sets),
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
        "project": args.project or evidence["project"],
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
