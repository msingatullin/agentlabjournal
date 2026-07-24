#!/usr/bin/env python3
"""Turn a reel structure analysis into an original two-host production brief."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def build(analysis: dict, topic: str, language: str = "ru") -> dict:
    funnel = analysis.get("funnel", {})
    tracked = funnel.get("tracked_url", "")
    if language == "en":
        scenes = [
            {"time": "0-5s", "speaker": "Host", "text": f"The usual advice about {topic} is backwards. Here is the practical version.", "visual": "Host close-up; title on screen."},
            {"time": "5-14s", "speaker": "Expert", "text": "Start with the outcome, then build the smallest repeatable workflow around it.", "visual": "Expert; three-step diagram."},
            {"time": "14-25s", "speaker": "Host", "text": "First, collect real examples. Second, extract the structure. Third, replace the examples with your own evidence.", "visual": "B-roll: source cards, transcript, checklist."},
            {"time": "25-38s", "speaker": "Expert", "text": "The important part is not copying a viral script. It is understanding why the opening, proof and next action work together.", "visual": "Split screen: structure map; no copied text."},
            {"time": "38-50s", "speaker": "Host", "text": "We turned this process into a repeatable content workflow and linked it to a full article.", "visual": "Article preview and funnel arrow."},
            {"time": "50-60s", "speaker": "Both", "text": "Open the article, take the framework, and build your own version. The link is in the description.", "visual": "Both characters; CTA and tracked URL."},
        ]
    else:
        scenes = [
            {"time": "0-5с", "speaker": "Ведущий", "text": f"Обычно про {topic} рассказывают слишком сложно. Вот рабочая схема.", "visual": "Крупный план ведущего; заголовок на экране."},
            {"time": "5-14с", "speaker": "Эксперт", "text": "Сначала определите результат, затем соберите вокруг него небольшой повторяемый процесс.", "visual": "Эксперт; схема из трёх шагов."},
            {"time": "14-25с", "speaker": "Ведущий", "text": "Первое: соберите реальные примеры. Второе: выделите структуру. Третье: замените чужие примеры собственными фактами.", "visual": "B-roll: карточки источников, транскрипция, чек-лист."},
            {"time": "25-38с", "speaker": "Эксперт", "text": "Главное — не копировать вирусный текст, а понять, как связаны начало, доказательство и следующий шаг.", "visual": "Карта структуры; чужой текст не показываем."},
            {"time": "38-50с", "speaker": "Ведущий", "text": "Мы превратили этот подход в повторяемый контентный процесс и связали его с полноценной статьёй.", "visual": "Превью статьи и стрелка воронки."},
            {"time": "50-60с", "speaker": "Оба", "text": "Откройте статью, заберите структуру и соберите свою версию. Ссылка в описании.", "visual": "Оба персонажа; CTA и UTM-ссылка."},
        ]
    return {
        "format": "vertical_reel_9x16",
        "language": language,
        "topic": topic,
        "duration_seconds": 60,
        "source_policy": "Structure only; no source wording or unsupported source claims.",
        "scenes": scenes,
        "production": {
            "voice": {"host": "male_voice", "expert": "female_voice"},
            "avatar": {"host": "master-reference-1", "expert": "master-reference-2"},
            "subtitles": True,
            "music": "low-volume, duck under speech",
            "cta_url": tracked,
        },
        "publication": {
            "channels": ["instagram_reels", "youtube_shorts", "x", "telegram"],
            "caption": f"{topic}: практическая схема без лишней теории. Полный разбор по ссылке.",
            "tracking": tracked,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--language", choices=["ru", "en"], default="ru")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.analysis.read_text(encoding="utf-8"))
    result = build(payload, args.topic, args.language)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"REEL_SCRIPT: generated {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
