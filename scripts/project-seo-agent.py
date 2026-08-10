#!/usr/bin/env python3
"""Build an evidence-backed podcast query passport from one project's SEO data."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from podcast_contract import read_json, write_json

STOP = {"и", "в", "на", "для", "как", "что", "это", "с", "по", "the", "of", "to", "a"}


def tokens(value: str) -> set[str]:
    words = re.findall(r"[a-zа-яё0-9]+", value.casefold().replace("ии", "ai"))
    return {word if word == "ai" else word[:5] for word in words if (len(word) > 2 or word == "ai") and word not in STOP}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--registry", type=Path, default=Path("/root/agentlabjournal/seo-project-agents.json"))
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package = read_json(args.package)
    registry = read_json(args.registry)
    project = registry.get("projects", {}).get(args.project_key)
    if not project:
        raise RuntimeError(f"SEO_PROJECT_AGENT: BLOCKED: unknown project {args.project_key}")
    if project.get("status") != "active":
        raise RuntimeError(f"SEO_PROJECT_AGENT: BLOCKED: {args.project_key} status={project.get('status')}")
    universe_path = Path(project["keyword_universe"])
    query_map_path = Path(project["query_map"])
    universe = read_json(universe_path)
    query_map = read_json(query_map_path)
    rows = universe.get("keywords", [])
    topic = " ".join([package.get("daily_topic", ""), package.get("listener_takeaway", "")])
    topic_tokens = tokens(topic)
    owned = {
        str(item.get("primary_query", "")).casefold(): item.get("target_url")
        for item in query_map.get("articles", {}).values() if isinstance(item, dict)
    }
    owned.update({
        str(item.get("primary_query", "")).casefold(): url
        for url, item in query_map.get("pages", {}).items() if isinstance(item, dict)
    })
    candidates = []
    for row in rows:
        query = str(row.get("query", "")).strip()
        overlap = topic_tokens & tokens(query)
        if not overlap or not isinstance(row.get("frequency_value"), int) or not row.get("frequency_class"):
            continue
        owner = owned.get(query.casefold())
        if owner and owner != args.canonical:
            continue
        class_rank = {"low": 3, "medium": 2, "high": 1}.get(row["frequency_class"], 0)
        coverage = len(overlap) / max(1, len(tokens(query)))
        weighted_overlap = sum(0.2 if token == "ai" else 0.5 if token in {"систе", "данны"} else 1.0 for token in overlap)
        candidates.append((weighted_overlap, coverage, len(overlap), class_rank, -row["frequency_value"], row))
    candidates.sort(reverse=True, key=lambda item: item[:5])
    if not candidates:
        raise RuntimeError("SEO_QUERY_GATE: BLOCKED: no measured project query matches episode intent")
    primary_pool = [item for item in candidates if item[5]["frequency_class"] in {"low", "medium"}] or candidates
    primary = primary_pool[0][5]
    related = []
    seen_classes = {primary["frequency_class"]}
    for _, _, _, _, _, row in candidates:
        if row["query"] == primary["query"]:
            continue
        if row["frequency_class"] not in seen_classes or len(related) < 2:
            related.append({"query": row["query"], "frequency_class": row["frequency_class"], "frequency_value": row["frequency_value"]})
            seen_classes.add(row["frequency_class"])
        if len(related) == 5:
            break
    passport = {
        "agent": project["agent_id"], "project_key": args.project_key, "project": universe.get("project"), "status": "OK",
        "seo_query_gate": "OK", "created_at": f"{package['date']}T00:00:00+00:00",
        "primary_query": primary["query"], "frequency_class": primary["frequency_class"],
        "frequency_value": primary["frequency_value"], "intent": "informational",
        "region": universe.get("region"), "language": "ru", "related_queries": related,
        "evidence_source": "yandex-wordstat", "evidence_ref": universe.get("source_evidence"),
        "evidence_collected_at": universe.get("collected_at"), "target_canonical_url": args.canonical,
        "parent_pillar_page": project["parent_pillar_page"],
        "internal_link_plan": [project["parent_pillar_page"]],
        "query_to_url_unique": True, "cannibalization_checked_against": str(query_map_path),
        "recommended_title": f"{primary['query'].capitalize().replace(' ai ', ' AI ')} — {package.get('daily_topic', '')}",
        "wordstat_evidence_root": project["raw_wordstat_root"],
    }
    write_json(args.output, passport)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
