#!/usr/bin/env python3
"""Generates distinct, high-res editorial covers (1200x675 16:9) for Dzen articles.
Uses Pillow to create clean, branded, thematic cards with tech gradients and typography.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ARTICLES = {
    "amocrm-ai-agent-implementation-checklist": {
        "title": "amoCRM AI-агент",
        "subtitle": "Чек-лист безопасного внедрения без потери заявок",
        "tag": "CRM & SALES",
        "accent": "#00A8FF", # Blue
        "bg_start": (10, 24, 45),
        "bg_end": (5, 12, 25)
    },
    "bitrix-mcp-server-boundary": {
        "title": "MCP-сервер для Битрикс24",
        "subtitle": "Границы инструментов, права и тестовый стенд",
        "tag": "INFRASTRUCTURE",
        "accent": "#00D2D3", # Cyan
        "bg_start": (8, 30, 40),
        "bg_end": (4, 15, 20)
    },
    "ai-estimate-agent-control": {
        "title": "AI-агент для расчёта смет",
        "subtitle": "Как проверять объёмы, цены и допущения",
        "tag": "FINANCE & B2B",
        "accent": "#FF9F43", # Amber
        "bg_start": (35, 25, 10),
        "bg_end": (18, 12, 5)
    },
    "hr-ai-agent-pilot": {
        "title": "AI-агенты в HR процессах",
        "subtitle": "Пилот без автоматических кадровых решений",
        "tag": "HR & TALENT",
        "accent": "#9B59B6", # Purple
        "bg_start": (28, 15, 40),
        "bg_end": (14, 8, 20)
    },
    "wildberries-ai-agent-operations": {
        "title": "AI-агент для Wildberries",
        "subtitle": "Контроль карточек, остатков и исключений",
        "tag": "E-COMMERCE",
        "accent": "#E056FD", # Magenta
        "bg_start": (35, 10, 35),
        "bg_end": (18, 5, 18)
    },
    "advertising-ai-agent-budget-guard": {
        "title": "AI-агент по рекламе",
        "subtitle": "Бюджетные лимиты, черновики и контроль публикации",
        "tag": "MARKETING & ADS",
        "accent": "#EE5253", # Red
        "bg_start": (40, 15, 15),
        "bg_end": (20, 8, 8)
    },
    "payment-acquiring-ai-agent-boundary": {
        "title": "AI в торговом эквайринге",
        "subtitle": "Где заканчивается рекомендация и начинается платёж",
        "tag": "FINTECH & PAYMENTS",
        "accent": "#10AC84", # Emerald
        "bg_start": (10, 35, 25),
        "bg_end": (5, 18, 12)
    },
    "local-llm-on-phone-test": {
        "title": "Локальная LLM на телефоне",
        "subtitle": "Тест памяти, скорости и приватности",
        "tag": "EDGE AI & MOBILE",
        "accent": "#48DBFB", # Light Blue
        "bg_start": (12, 30, 48),
        "bg_end": (6, 15, 24)
    },
    "local-llm-for-1c-boundary": {
        "title": "Локальная LLM для 1С",
        "subtitle": "Безопасная граница между текстом и учётными данными",
        "tag": "ENTERPRISE 1C",
        "accent": "#F368E0", # Pink/Orange
        "bg_start": (40, 20, 30),
        "bg_end": (20, 10, 15)
    },
    "n8n-ai-agent-production-checklist": {
        "title": "AI-агенты в n8n",
        "subtitle": "Production-чек-лист после первого workflow",
        "tag": "AUTOMATION & WORKFLOWS",
        "accent": "#FF6B6B", # Coral
        "bg_start": (38, 18, 18),
        "bg_end": (19, 9, 9)
    }
}

WIDTH = 1200
HEIGHT = 675

def get_font(size: int, bold: bool = False):
    font_names = [
        "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf" if bold else "/usr/share/fonts/truetype/montserrat/Montserrat-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for fn in font_names:
        if Path(fn).exists():
            return ImageFont.truetype(fn, size)
    return ImageFont.load_default()

def draw_gradient(draw: ImageDraw.ImageDraw, start_color, end_color):
    for y in range(HEIGHT):
        r = int(start_color[0] + (end_color[0] - start_color[0]) * (y / HEIGHT))
        g = int(start_color[1] + (end_color[1] - start_color[1]) * (y / HEIGHT))
        b = int(start_color[2] + (end_color[2] - start_color[2]) * (y / HEIGHT))
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

def create_cover(slug: str, info: dict, out_path: Path):
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    # 1. Background gradient
    draw_gradient(draw, info["bg_start"], info["bg_end"])
    
    # 2. Modern decorative grid / lines
    accent_rgb = tuple(int(info["accent"].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    for x in range(0, WIDTH, 80):
        draw.line([(x, 0), (x, HEIGHT)], fill=(255, 255, 255, 12), width=1)
    for y in range(0, HEIGHT, 80):
        draw.line([(0, y), (WIDTH, y)], fill=(255, 255, 255, 12), width=1)
        
    # Subtle glowing bar on left edge
    draw.rectangle([(0, 0), (12, HEIGHT)], fill=accent_rgb)

    # 3. Top Header: Brand + Tag Badge
    font_brand = get_font(26, bold=True)
    font_tag = get_font(20, bold=True)
    
    draw.text((60, 60), "AGENT LAB JOURNAL", fill=(180, 200, 220), font=font_brand)
    
    # Tag Badge
    tag_text = f"  {info['tag']}  "
    tag_bbox = draw.textbbox((0, 0), tag_text, font=font_tag)
    tag_w = tag_bbox[2] - tag_bbox[0]
    tag_h = tag_bbox[3] - tag_bbox[1] + 14
    badge_x = WIDTH - tag_w - 60
    badge_y = 56
    draw.rounded_rectangle([(badge_x, badge_y), (badge_x + tag_w, badge_y + tag_h)], radius=6, fill=accent_rgb)
    draw.text((badge_x + 8, badge_y + 6), info["tag"], fill=(255, 255, 255), font=font_tag)

    # 4. Main Article Title
    font_title = get_font(58, bold=True)
    font_sub = get_font(32, bold=False)
    
    title_text = info["title"]
    draw.text((60, 240), title_text, fill=(255, 255, 255), font=font_title)
    
    # Subtitle wrapping
    sub_words = info["subtitle"].split()
    sub_lines = []
    curr = []
    for w in sub_words:
        if len(" ".join(curr + [w])) > 45:
            sub_lines.append(" ".join(curr))
            curr = [w]
        else:
            curr.append(w)
    if curr:
        sub_lines.append(" ".join(curr))
        
    y_cursor = 330
    for line in sub_lines:
        draw.text((60, y_cursor), line, fill=(200, 215, 230), font=font_sub)
        y_cursor += 44
        
    # 5. Bottom verified badge
    font_footer = get_font(22, bold=False)
    draw.line([(60, HEIGHT - 90), (WIDTH - 60, HEIGHT - 90)], fill=(60, 80, 105), width=1)
    draw.text((60, HEIGHT - 65), "✓ Проверенная инженерная архитектура · Редакция 2026", fill=(140, 165, 190), font=font_footer)
    draw.text((WIDTH - 240, HEIGHT - 65), "dzen.ru/agentlab", fill=accent_rgb, font=font_footer)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), "PNG", optimize=True)
    print(f"Generated cover: {out_path.name}")

def main():
    root = Path("/root/agentlabjournal")
    covers_dir = root / "assets" / "covers"
    covers_json_path = root / "homepage-covers.json"
    covers_data = json.loads(covers_json_path.read_text(encoding="utf-8")) if covers_json_path.exists() else {}

    for slug, info in ARTICLES.items():
        cover_filename = f"dzen-cover-{slug}.png"
        cover_file = covers_dir / cover_filename
        create_cover(slug, info, cover_file)
        
        rel_path = f"assets/covers/{cover_filename}"
        covers_data[slug] = {
            "path": rel_path,
            "social_path": rel_path,
            "alt": f"{info['title']}: {info['subtitle']}",
            "evidence": "generated unique editorial cover for Dzen RSS",
            "type": "editorial-unique-cover",
            "publication_status": "approved"
        }
        
        # Update HTML meta og:image
        html_file = root / f"{slug}.html"
        if html_file.exists():
            html_content = html_file.read_text(encoding="utf-8")
            new_og = f'https://agentlabjournal.online/{rel_path}'
            # Replace old og:image
            html_content = re.sub(
                r'<meta property="og:image" content="[^"]+">',
                f'<meta property="og:image" content="{new_og}">',
                html_content
            )
            html_file.write_text(html_content, encoding="utf-8")
            print(f"Updated og:image in {slug}.html")

    covers_json_path.write_text(json.dumps(covers_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Updated homepage-covers.json successfully!")

if __name__ == "__main__":
    main()
