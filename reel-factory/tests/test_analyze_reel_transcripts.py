import importlib.util
from pathlib import Path


path = Path(__file__).parents[1] / "scripts" / "analyze-reel-transcripts.py"
spec = importlib.util.spec_from_file_location("reel_analyzer", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_extracts_structure_and_utm():
    result = module.analyze("Как создать ролик? Сначала соберите примеры. Затем проверьте результат. Переходите по ссылке.", "https://example.com/a")
    assert result["structure"]["hook"].startswith("Как создать")
    assert result["structure"]["cta_examples"]
    assert "utm_source=instagram" in result["funnel"]["tracked_url"]


def test_originality_guardrails_present():
    result = module.analyze("Текст источника.")
    assert any("Do not reuse" in rule for rule in result["originality_guardrails"])
