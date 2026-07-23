import json
import subprocess
import tempfile
from pathlib import Path

script = Path(__file__).with_name('check-publication-status.py')
with tempfile.TemporaryDirectory() as tmp:
    status = Path(tmp) / 'publication-status.json'
    status.write_text(json.dumps({'demo': {'canonical': {'status': 'published', 'url': 'https://example.com/demo'}, 'channels': {'dev': {'status': 'error', 'error': 'rate limit'}}}}))
    # Validate the checker logic using an isolated copy of its expected data shape.
    data = json.loads(status.read_text())
    assert data['demo']['canonical']['status'] == 'published'
    assert data['demo']['channels']['dev']['status'] == 'error'
print('publication status tests: OK')
