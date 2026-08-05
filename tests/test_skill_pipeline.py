import json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_registry_is_fail_closed():
    data=json.loads((ROOT/'skills/registry.json').read_text())
    assert data['seo_gate']=='fail_closed'
    assert data['external_publish']=='manual_approval_only'

def test_distribution_pack_is_draft():
    r=subprocess.run([sys.executable,str(ROOT/'scripts/build-content-pack.py'),'--file','agent-release-checklist.html'],cwd=ROOT,text=True,capture_output=True)
    assert r.returncode==0, r.stdout+r.stderr
    pack=json.loads((ROOT/'out/distribution/agent-release-checklist.json').read_text())
    assert pack['status']=='draft'
    assert pack['manual_review_required'] is True
    assert 'utm_source=' in pack['tracked_url']
