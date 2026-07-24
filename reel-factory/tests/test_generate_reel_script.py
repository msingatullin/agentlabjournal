import importlib.util
from pathlib import Path


def load(name):
    path = Path(__file__).parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builds_two_host_script_with_tracking():
    module = load("generate-reel-script")
    result = module.build({"funnel": {"tracked_url": "https://example.com/a?utm_source=instagram"}}, "AI agents")
    assert len(result["scenes"]) == 6
    assert result["production"]["avatar"]["host"] == "master-reference-1"
    assert "utm_source=instagram" in result["publication"]["tracking"]
