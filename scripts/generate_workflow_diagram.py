from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


OUTPUT_PATH = Path(r"D:\cxdownload\kg agent\kg_agent_app\docs\workflow_with_entity_normalization.png")
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")

WIDTH = 1500
HEIGHT = 1700


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size)


def rounded_box(draw: ImageDraw.ImageDraw, xy, fill, outline=None, radius=18, width=2):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def centered_text(draw: ImageDraw.ImageDraw, xy, lines, font, fill, line_gap=8):
    if isinstance(lines, str):
        lines = [lines]
    widths = []
    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    x0, y0, x1, y1 = xy
    y = y0 + (y1 - y0 - total_h) / 2
    for i, line in enumerate(lines):
        w = widths[i]
        h = heights[i]
        x = x0 + (x1 - x0 - w) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += h + line_gap


def arrow(draw: ImageDraw.ImageDraw, start, end, fill=(70, 66, 66), width=4, label=None, label_offset=(0, 0), bend=None):
    if bend:
        points = [start, bend, end]
        draw.line(points, fill=fill, width=width)
        p1, p2 = bend, end
    else:
        draw.line([start, end], fill=fill, width=width)
        p1, p2 = start, end
    import math
    angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    arrow_len = 18
    arrow_angle = math.pi / 7
    left = (
        end[0] - arrow_len * math.cos(angle - arrow_angle),
        end[1] - arrow_len * math.sin(angle - arrow_angle),
    )
    right = (
        end[0] - arrow_len * math.cos(angle + arrow_angle),
        end[1] - arrow_len * math.sin(angle + arrow_angle),
    )
    draw.polygon([end, left, right], fill=fill)
    if label:
        font = load_font(32)
        bbox = draw.textbbox((0, 0), label, font=font)
        lx = (start[0] + end[0]) / 2 - (bbox[2] - bbox[0]) / 2 + label_offset[0]
        ly = (start[1] + end[1]) / 2 - (bbox[3] - bbox[1]) / 2 + label_offset[1]
        draw.text((lx, ly), label, font=font, fill=(34, 34, 34))


def main() -> None:
    img = Image.new("RGBA", (WIDTH, HEIGHT), (247, 249, 252, 255))
    bg = Image.new("RGBA", (WIDTH, HEIGHT), (247, 249, 252, 255))
    bg_draw = ImageDraw.Draw(bg)

    soft_colors = [
        ((220, 207, 243, 120), (420, 90, 740, 260)),
        ((251, 244, 191, 120), (290, 250, 860, 470)),
        ((247, 203, 205, 125), (120, 525, 590, 780)),
        ((254, 224, 182, 120), (80, 820, 640, 1045)),
        ((182, 216, 247, 140), (670, 1020, 1180, 1275)),
        ((220, 246, 213, 135), (60, 1080, 535, 1320)),
        ((224, 207, 242, 120), (760, 1320, 1110, 1480)),
        ((247, 198, 191, 140), (455, 1540, 810, 1690)),
        ((222, 247, 212, 135), (955, 1540, 1480, 1690)),
        ((248, 234, 207, 120), (520, 460, 940, 670)),
    ]

    for color, box in soft_colors:
        bg_draw.rounded_rectangle(box, radius=44, fill=color)

    bg = bg.filter(ImageFilter.GaussianBlur(48))
    img.alpha_composite(bg)
    draw = ImageDraw.Draw(img)

    title_font = load_font(36)
    body_font = load_font(34)
    small_font = load_font(30)

    node_styles = {
        "purple": ((233, 220, 246, 235), (219, 205, 239, 255)),
        "yellow": ((249, 246, 199, 235), (240, 232, 166, 255)),
        "pink": ((249, 199, 203, 238), (238, 177, 184, 255)),
        "peach": ((250, 224, 182, 238), (239, 205, 154, 255)),
        "blue": ((185, 219, 248, 238), (154, 196, 233, 255)),
        "green": ((220, 246, 213, 238), (194, 228, 188, 255)),
    }

    boxes = {
        "user": ((480, 80, 770, 180), "purple", ["用户输入问题"]),
        "parse": ((405, 220, 845, 340), "purple", ["query_parse:", "识别人名 / 流派实体"]),
        "normalize": ((350, 380, 900, 510), "peach", ["entity_normalize:", "别名归一并映射到图谱标准实体"]),
        "decide": ((310, 560, 860, 690), "yellow", ["llm_decide_tool:", "大模型判断是否调用工具"]),
        "tools": ((170, 840, 590, 975), "pink", ["tools: ToolNode", "执行固定查询工具"]),
        "after": ((120, 1115, 640, 1235), "peach", ["after_tool: 检查工具结果"]),
        "tool_answer": ((0, 1365, 530, 1500), "green", ["LLM", "根据工具结果组织中文回答"]),
        "sparql_gen": ((640, 1115, 1185, 1260), "blue", ["generate_sparql: LLM 或", "few-shot 生成 SPARQL"]),
        "sparql_exec": ((760, 1385, 1120, 1490), "purple", ["执行 SPARQL 查询"]),
        "sparql_answer": ((500, 1560, 860, 1685), "pink", ["LLM 根据 SPARQL", "结果组织回答"]),
        "fallback": ((980, 1560, 1495, 1685), "green", ["fallback:", "兜底说明或大模型参考回答"]),
    }

    for _, (xy, style_key, lines) in boxes.items():
        fill, outline = node_styles[style_key]
        rounded_box(draw, xy, fill=fill, outline=outline, radius=18, width=2)
        font = title_font if len(lines) == 1 else body_font
        centered_text(draw, xy, lines, font=font, fill=(24, 24, 24), line_gap=10)

    arrow(draw, (625, 180), (625, 220))
    arrow(draw, (625, 340), (625, 380))
    arrow(draw, (625, 510), (625, 560))
    arrow(draw, (430, 690), (380, 840), label="选择工具", label_offset=(-35, -28))
    arrow(draw, (380, 975), (380, 1115))
    arrow(draw, (265, 1235), (255, 1365), label="有 rows", label_offset=(-48, -20))
    arrow(draw, (500, 1235), (760, 1115), label="无 rows / 工具失败", label_offset=(10, -24))
    arrow(draw, (1020, 640), (1020, 1115), label="不调用工具", label_offset=(74, -34), bend=(1020, 885))
    arrow(draw, (915, 1260), (940, 1385))
    arrow(draw, (900, 1490), (700, 1560), label="有结果", label_offset=(-25, -28))
    arrow(draw, (1040, 1490), (1230, 1560), label="失败 / 无法生成", label_offset=(56, -30))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(OUTPUT_PATH, quality=95)


if __name__ == "__main__":
    main()
