#!/usr/bin/env python3
"""Build a deterministic traffic->lead->money report from CRM CSV and optional metrics JSON."""
from __future__ import annotations
import argparse, csv, datetime as dt, json
from collections import Counter
from pathlib import Path

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--crm', default='/root/agentlabjournal/crm-template/leads.csv')
    p.add_argument('--metrics-json', help='Optional measured traffic/events JSON; no guessing when absent')
    p.add_argument('--since', help='ISO date, default 7 days ago')
    p.add_argument('--out', default='/root/wiki/system/weekly-funnel-report.md')
    a = p.parse_args()
    end = dt.date.today(); start = dt.date.fromisoformat(a.since) if a.since else end - dt.timedelta(days=7)
    rows=[]
    with open(a.crm, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            try: d=dt.datetime.fromisoformat(r.get('submitted_at','').replace('Z','+00:00')).date()
            except Exception: continue
            if start <= d <= end: rows.append(r)
    statuses=Counter(r.get('status','unknown') for r in rows)
    sources=Counter((r.get('utm_source') or 'unknown') for r in rows)
    paid=sum(1 for r in rows if r.get('payment_received','').lower() in {'true','1','yes'})
    revenue=sum(float(r.get('offer_price') or 0) for r in rows if r.get('payment_received','').lower() in {'true','1','yes'})
    metrics={}
    if a.metrics_json:
        metrics=json.loads(Path(a.metrics_json).read_text(encoding='utf-8'))
    lines=[f'# Weekly funnel report: {start} — {end}','', '## Measured CRM data', '',
           f'- Leads: **{len(rows)}**', f'- Paid leads: **{paid}**', f'- Recorded revenue: **{revenue:.2f} RUB**',
           f'- Statuses: `{dict(statuses)}`', f'- UTM sources: `{dict(sources)}`', '',
           '## Traffic and conversion', '', 'Only supplied measurements are shown; absent metrics are `NOT CONFIRMED`.']
    for key in ('sessions','article_views','lead_cta_clicks','form_starts','lead_submitted_success','conversion_rate'):
        lines.append(f'- {key}: **{metrics.get(key, "NOT CONFIRMED")}**')
    lines += ['', '## Limitations', '', '- CRM rows without a valid ISO `submitted_at` are excluded.', '- Revenue is based only on rows with `payment_received=true`; cash not recorded in CRM is not inferred.']
    Path(a.out).write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'rows': len(rows), 'out': a.out}, ensure_ascii=False)); return 0
if __name__ == '__main__': raise SystemExit(main())
