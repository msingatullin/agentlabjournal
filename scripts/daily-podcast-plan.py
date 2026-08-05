#!/usr/bin/env python3
"""Collect previous-24h research in NotebookLM and create a dated editorial brief."""
from __future__ import annotations
import argparse, datetime as dt, json, re, subprocess
from pathlib import Path

ROOT=Path('/root'); NB='fb0f2035-2378-47c1-9add-e7f27b223d56'; NLC='/root/.venvs/notebooklm/bin/notebooklm'
RUBRICS=['Новости недели','AI в работу','Человек vs Машина','Под капот','AI в России','Будущее рядом','Вопрос слушателя']

def run(cmd): return subprocess.run(cmd, text=True, capture_output=True, check=True).stdout

def extract_selection(payload):
 answer=payload.get('answer') if isinstance(payload,dict) else None
 if not isinstance(answer,str): return payload
 match=re.search(r'```(?:json)?\s*(\{.*\})\s*```',answer,re.S)
 candidate=match.group(1) if match else answer.strip()
 parsed=json.loads(candidate)
 if not isinstance(parsed,dict): raise ValueError('NotebookLM selection is not an object')
 return parsed

def main():
 p=argparse.ArgumentParser(); p.add_argument('--date',default=dt.date.today().isoformat()); p.add_argument('--notebook',default=NB); p.add_argument('--no-research',action='store_true'); a=p.parse_args()
 day=dt.date.fromisoformat(a.date); rubric=RUBRICS[day.weekday()]
 if not a.no_research:
  q=(f'Найди и добавь в этот блокнот только проверяемые AI/IT новости за последние 24 часа на дату {a.date}. '
     'Приоритет: официальные блоги компаний, регуляторы, научные публикации и первичные документы. Не импортируй дубли и рекламные пересказы.')
  subprocess.run([NLC,'source','add-research','-n',a.notebook,'--from','web','--mode','fast','--import-all','--cited-only','--timeout','900',q],check=False)
 prompt=(f'Ты редактор Agent Lab Journal Podcast. Дата: {a.date}. Рубрика дня: {rubric}. '
  'Выбери 2–3 самые важные новости строго за последние 24 часа из источников блокнота. '
  'Для каждой укажи title, date, primary_source, claim, why_it_matters, confidence. '
  'Если данных мало, укажи insufficient_data. Затем выбери одну тему дня и практический угол для предпринимателя. '
  'Верни JSON с ключами news, daily_topic, listener_takeaway, source_ids. Не выдумывай.')
 raw=run([NLC,'ask','-n',a.notebook,'--new','--yes','--json',prompt])
 data=json.loads(raw); selection=extract_selection(data)
 required=('news','daily_topic','listener_takeaway','source_ids')
 if any(not selection.get(key) for key in required): raise ValueError('NotebookLM selection misses required fields')
 out={'date':a.date,'rubric':rubric,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'notebook':a.notebook,'selection':selection}
 path=ROOT/'wiki/system'/f'daily-podcast-plan-{a.date}.json'; path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(path); return 0
if __name__=='__main__': raise SystemExit(main())
