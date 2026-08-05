#!/usr/bin/env python3
"""Store feedback for later human-approved skill revision; never edits a skill silently."""
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
def main():
    p=argparse.ArgumentParser(); p.add_argument('--skill',required=True); p.add_argument('--feedback',required=True); p.add_argument('--source',default='owner')
    a=p.parse_args(); out=ROOT/'out'/'skill-feedback.jsonl'; out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('a',encoding='utf-8') as f: f.write(json.dumps({'skill':a.skill,'feedback':a.feedback,'source':a.source,'status':'pending_review','at':datetime.now(timezone.utc).isoformat()},ensure_ascii=False)+'\n')
    print(f'FEEDBACK_RECORDED: {out.relative_to(ROOT)} status=pending_review')
if __name__=='__main__': main()
