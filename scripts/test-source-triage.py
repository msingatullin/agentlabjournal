import importlib.util
from pathlib import Path

path = Path(__file__).with_name('triage-article-sources.py')
spec = importlib.util.spec_from_file_location('triage', path)
# The production script performs I/O at import time, so test the deterministic rules
# by extracting only the function definitions.
source = path.read_text()
prefix = source.split('known_titles =', 1)[0]
namespace = {}
namespace['__file__'] = str(path)
exec(compile(prefix, str(path), 'exec'), namespace)

assert namespace['source_quality']({'url': 'https://github.com/example/repo'}) == 'known_platform'
assert namespace['source_quality']({'url': 'https://example.invalid/post'}) == 'unknown'
assert namespace['normalized_title']('AI: Agents — Test!') == 'ai agents test'
print('source triage tests: OK')
