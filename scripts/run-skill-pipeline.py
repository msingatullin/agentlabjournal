#!/usr/bin/env python3
"""Deterministic local dispatcher for Agent Lab skills.

It produces artifacts and never publishes externally. Every stage is logged.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "skills/registry.json"
LOG = ROOT / "out/skill-runs.jsonl"

def record(run_id, stage, status, detail=""):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"run_id":run_id,"stage":stage,"status":status,
                            "detail":detail,"at":datetime.now(timezone.utc).isoformat()}, ensure_ascii=False)+"\n")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--metrics-json")
    p.add_argument("--strategy-json")
    a=p.parse_args()
    article=ROOT/a.file
    if not article.exists(): raise SystemExit(f"SKILL_PIPELINE: BLOCKED article not found: {a.file}")
    run_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    record(run_id,"START","OK",a.file)

    result=subprocess.run([sys.executable,str(ROOT/"scripts/check-publication.py")],cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        record(run_id,"publication-gate","BLOCKED",result.stdout[-2000:])
        print("SKILL_PIPELINE: BLOCKED publication gate")
        return result.returncode
    record(run_id,"publication-gate","OK")

    html=article.read_text(encoding="utf-8")
    required=("canonical","description","Article")
    missing=[x for x in required if x.lower() not in html.lower()]
    if missing:
        record(run_id,"source-fact-check","BLOCKED",f"missing markers: {missing}")
        print(f"SKILL_PIPELINE: BLOCKED source/metadata markers: {missing}")
        return 1
    record(run_id,"source-fact-check","OK","article-local facts only")

    result=subprocess.run([sys.executable,str(ROOT/"scripts/build-content-pack.py"),"--file",a.file],cwd=ROOT,text=True,capture_output=True)
    if result.returncode:
        record(run_id,"article-to-distribution","BLOCKED",result.stdout[-2000:]+result.stderr[-1000:])
        print("SKILL_PIPELINE: BLOCKED distribution pack")
        return result.returncode
    record(run_id,"article-to-distribution","OK",result.stdout.strip())

    if a.metrics_json:
        result=subprocess.run([sys.executable,str(ROOT/"scripts/weekly-funnel-report.py"),"--metrics-json",a.metrics_json],cwd=ROOT,text=True,capture_output=True)
        status="OK" if result.returncode==0 else "BLOCKED"
        record(run_id,"weekly-funnel-review",status,result.stdout[-2000:]+result.stderr[-1000:])
        if result.returncode: return result.returncode
    else:
        record(run_id,"weekly-funnel-review","SKIPPED","no measured metrics supplied")

    strategy={"status":"draft","fit":"needs_owner_review","next_48h_action":"review distribution draft and choose one channel","stop_criteria":["no measured demand","no confirmed source","manual approval absent"]}
    if a.strategy_json:
        strategy.update(json.loads(Path(a.strategy_json).read_text(encoding="utf-8")))
    out=ROOT/"out"/"strategy"/f"{article.stem}.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(strategy,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    record(run_id,"strategic-advisor","OK",str(out.relative_to(ROOT)))
    record(run_id,"COMMIT","OK","artifacts only; external publication not performed")
    print(f"SKILL_PIPELINE: OK run={run_id} distribution=manual-review strategy={out.relative_to(ROOT)}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
