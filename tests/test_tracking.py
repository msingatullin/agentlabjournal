import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from tracking import tracked_url


def test_tracking_contains_language_country_region_and_article():
    url = tracked_url('https://agentlabjournal.online/en/test.html', 'x', 'social', 'test-article', 'en', 'us', 'california', 'post')
    assert 'utm_source=x' in url
    assert 'utm_campaign=agentlabjournal-en-us-california' in url
    assert 'utm_content=post' in url
    assert 'utm_term=test-article' in url
