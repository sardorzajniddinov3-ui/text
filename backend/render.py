import io
import os
import random
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageFont

# Размеры листа приблизительно как А4 при 150 dpi
PAGE_WIDTH = 1240
PAGE_HEIGHT = 1754

# Размер холста для обучения на фронтенде (260x260)
RAW_CANVAS_SIZE = 260
# Базовая линия на холсте 260x260
CANVAS_BASELINE = 180

# Пресеты размера текста: настроены для идеальной чёткости и читаемости,
# с естественным межбуквенным интервалом (буквы не слипаются в кашу).
FONT_PRESETS = {
    "compact": {
        "label": "Мелкий (максимум текста)",
        "scale": 0.17,
        "line_height": 50,
        "line_ascent": 35,
        "space_width": 15,
        "letter_spacing": 1,
        "margin_x": 80,
        "margin_top": 75,
        "margin_bottom": 65,
    },
    "standard": {
        "label": "Стандартный (чёткий и читабельный)",
        "scale": 0.21,
        "line_height": 58,
        "line_ascent": 42,
        "space_width": 18,
        "letter_spacing": 2,
        "margin_x": 85,
        "margin_top": 80,
        "margin_bottom": 70,
    },
    "large": {
        "label": "Крупный",
        "scale": 0.26,
        "line_height": 72,
        "line_ascent": 51,
        "space_width": 22,
        "letter_spacing": 3,
        "margin_x": 90,
        "margin_top": 90,
        "margin_bottom": 80,
    },
}
DEFAULT_FONT_SIZE = "standard"


def get_font_params(font_size=DEFAULT_FONT_SIZE):
    """Возвращает параметры шрифта для заданного размера (пресет или число)."""
    if isinstance(font_size, (int, float)):
        scale = max(0.12, min(0.35, float(font_size)))
        line_height = max(36, round(scale * 280))
        line_ascent = round(CANVAS_BASELINE * scale) + 4
        space_width = max(12, round(scale * 85))
        letter_spacing = max(1, round(scale * 10))
        return {
            "scale": scale,
            "line_height": line_height,
            "line_ascent": line_ascent,
            "space_width": space_width,
            "letter_spacing": letter_spacing,
            "margin_x": 85,
            "margin_top": 80,
            "margin_bottom": 70,
        }
    return FONT_PRESETS.get(str(font_size).lower()) or FONT_PRESETS[DEFAULT_FONT_SIZE]


# ---------------------------------------------------------------------------
# Варианты бумаги - фон страницы, на котором составляется текст
# ---------------------------------------------------------------------------

def _blank_background(size, **kwargs):
    return Image.new("RGB", size, (255, 255, 255))


def _lined_background(size, line_height=58, line_ascent=42, margin_top=80, **kwargs):
    """Линии как в линованной тетради, точно выровненные под строки текста."""
    img = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(img)
    color = (205, 220, 240)
    y = margin_top + line_ascent + 4
    while y < size[1] - 25:
        draw.line([(30, y), (size[0] - 30, y)], fill=color, width=1)
        y += line_height
    return img


def _grid_background(size, **kwargs):
    """Клетчатая бумага (~5 мм клетка, стандарт тетради в клетку)."""
    img = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(img)
    step = 30  # ~5 мм при 150 DPI
    color = (220, 230, 244)
    for gx in range(0, size[0], step):
        draw.line([(gx, 0), (gx, size[1])], fill=color, width=1)
    for gy in range(0, size[1], step):
        draw.line([(0, gy), (size[0], gy)], fill=color, width=1)
    return img


def _margin_background(size, line_height=58, line_ascent=42, margin_top=80, margin_x=85, **kwargs):
    """Тетрадный лист: линии + красная вертикальная линия полей слева."""
    img = _lined_background(size, line_height=line_height, line_ascent=line_ascent, margin_top=margin_top)
    draw = ImageDraw.Draw(img)
    margin_line_x = margin_x - 18
    draw.line([(margin_line_x, 0), (margin_line_x, size[1])], fill=(215, 80, 90), width=2)
    return img


def _vintage_background(size, **kwargs):
    """Состаренная кремовая бумага с лёгкой плавной виньеткой по краям."""
    base = Image.new("RGB", size, (246, 237, 214))
    grad = ImageOps.invert(Image.radial_gradient("L"))
    grad = grad.resize(size, Image.BICUBIC)
    lut = [int(185 + (v / 255) * 70) for v in range(256)]
    grad = grad.point(lut)
    gradient_rgb = Image.merge("RGB", (grad, grad, grad))
    return ImageChops.multiply(base, gradient_rgb)


PAPER_STYLES = {
    "blank": {"label": "Чистый лист", "background": _blank_background},
    "lined": {"label": "Линованный лист", "background": _lined_background},
    "grid": {"label": "Клетка", "background": _grid_background},
    "margin": {"label": "Тетрадный лист", "background": _margin_background},
    "vintage": {"label": "Состаренная бумага", "background": _vintage_background},
}
DEFAULT_PAPER = "blank"


def get_paper_background(key, size, **kwargs):
    style = PAPER_STYLES.get(key) or PAPER_STYLES[DEFAULT_PAPER]
    return style["background"](size, **kwargs)


def list_paper_styles():
    return [{"key": key, "label": style["label"]} for key, style in PAPER_STYLES.items()]


def list_font_sizes():
    return [{"key": k, "label": v["label"]} for k, v in FONT_PRESETS.items()]


HANDWRITING_STYLES = {
    "my_handwriting": {
        "id": "my_handwriting",
        "name": "Мой личный почерк",
        "badge": "Обученный",
        "description": "Собственные буквы и связки, сохранённые в профиле",
        "font_family": "'Marck Script', cursive",
        "font_file": "MarckScript-Regular.ttf",
        "sample_preview": "Мой личный почерк",
        "use_samples": True,
    },
    "calligraphy": {
        "id": "calligraphy",
        "name": "Школьный каллиграфический",
        "badge": "Прописи",
        "description": "Классические ровные школьные прописи с правильным наклоном",
        "font_family": "'Marck Script', cursive",
        "font_file": "MarckScript-Regular.ttf",
        "sample_preview": "Школьные прописи",
        "use_samples": False,
    },
    "student": {
        "id": "student",
        "name": "Студенческий конспект",
        "badge": "Быстрый",
        "description": "Живой, беглый лекционный почерк студента",
        "font_family": "'Caveat', cursive",
        "font_file": "Caveat.ttf",
        "sample_preview": "Студенческий конспект",
        "use_samples": False,
    },
    "casual": {
        "id": "casual",
        "name": "Повседневный блокнот",
        "badge": "Мягкий",
        "description": "Непринуждённый мягкий почерк гелевой ручкой",
        "font_family": "'Bad Script', cursive",
        "font_file": "BadScript.ttf",
        "sample_preview": "Заметки в блокноте",
        "use_samples": False,
    },
    "architect": {
        "id": "architect",
        "name": "Чертёжный полупечатный",
        "badge": "Чёткий",
        "description": "Чёткий, аккуратный архитектурный стиль, идеален для формул",
        "font_family": "'Neucha', cursive",
        "font_file": "Neucha.ttf",
        "sample_preview": "Чертёжный полупечатный",
        "use_samples": False,
    },
    "expressive": {
        "id": "expressive",
        "name": "Размашистый авторский",
        "badge": "Широкий",
        "description": "Крупный, плавный, округлый почерк с широким шагом",
        "font_family": "'Pacifico', cursive",
        "font_file": "Pacifico-Regular.ttf",
        "sample_preview": "Размашистый почерк",
        "use_samples": False,
    },
}
DEFAULT_STYLE = "my_handwriting"


def list_handwriting_styles():
    return list(HANDWRITING_STYLES.values())


def _find_font_path(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "fonts", filename),
        os.path.join(os.path.dirname(base_dir), "frontend", "fonts", filename),
        os.path.join(base_dir, filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def _render_font_glyph(char, font_path, scale=0.21, ink_color=(34, 40, 59)):
    if not font_path or not os.path.exists(font_path):
        return None
    try:
        font = ImageFont.truetype(font_path, 150)
    except Exception:
        return None

    canvas_w, canvas_h = 260, 260
    im = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    r, g, b = (ink_color[0], ink_color[1], ink_color[2]) if len(ink_color) >= 3 else (34, 40, 59)
    d.text((40, 45), char, fill=(r, g, b, 240), font=font)

    crop_box = im.getbbox()
    if not crop_box:
        return None

    cropped = im.crop((crop_box[0], 0, crop_box[2], canvas_h))
    w, h = cropped.size
    if w == 0 or h == 0:
        return None

    new_w = max(1, round(w * scale))
    new_h = max(1, round(h * scale))
    scaled = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

    sw, sh = scaled.size
    baseline_scaled = round(CANVAS_BASELINE * scale)

    return GlyphData(
        image=scaled,
        exit_x=max(1, sw - 1),
        exit_y=baseline_scaled,
        entry_x=0,
        entry_y=baseline_scaled,
        ink_color=(r, g, b),
        stroke_width=max(1.5, round(scale * 9)),
    )



class GlyphData:
    def __init__(self, image, exit_x, exit_y, entry_x, entry_y, ink_color, stroke_width):
        self.image = image
        self.size = image.size
        self.width = image.width
        self.height = image.height
        self.exit_x = exit_x
        self.exit_y = exit_y
        self.entry_x = entry_x
        self.entry_y = entry_y
        self.ink_color = ink_color
        self.stroke_width = stroke_width


def _load_glyph(path, scale=0.21):
    """Загружает сохранённый образец буквы или связки, вычисляет точки выхода и входа."""
    img = Image.open(path).convert("RGBA")
    bbox = img.getbbox()
    if not bbox:
        return None
    cropped = img.crop((bbox[0], 0, bbox[2], img.height))
    w, h = cropped.size
    if h == 0 or w == 0:
        return None
    new_w = max(1, round(w * scale))
    new_h = max(1, round(h * scale))
    scaled = cropped.resize((new_w, new_h), Image.LANCZOS)

    sw, sh = scaled.size
    r_pts = []
    for x in range(sw - 1, max(-1, sw - 6), -1):
        for y in range(sh):
            pix = scaled.getpixel((x, y))
            if pix[3] > 40:
                r_pts.append((x, y, pix[3]))
        if r_pts:
            break

    l_pts = []
    for x in range(0, min(sw, 6)):
        for y in range(sh):
            pix = scaled.getpixel((x, y))
            if pix[3] > 40:
                l_pts.append((x, y, pix[3]))
        if l_pts:
            break

    baseline_scaled = round(CANVAS_BASELINE * scale)
    exit_y = sum(p[1] * p[2] for p in r_pts) / sum(p[2] for p in r_pts) if r_pts else baseline_scaled
    entry_y = sum(p[1] * p[2] for p in l_pts) / sum(p[2] for p in l_pts) if l_pts else baseline_scaled
    exit_x = r_pts[0][0] if r_pts else sw - 1
    entry_x = l_pts[0][0] if l_pts else 0

    ink_colors = [scaled.getpixel((x, y))[:3] for x in range(sw) for y in range(sh) if scaled.getpixel((x, y))[3] > 180]
    avg_color = (
        round(sum(c[0] for c in ink_colors) / len(ink_colors)) if ink_colors else 34,
        round(sum(c[1] for c in ink_colors) / len(ink_colors)) if ink_colors else 40,
        round(sum(c[2] for c in ink_colors) / len(ink_colors)) if ink_colors else 59,
    )
    stroke_w = max(1.5, round(scale * 10))

    return GlyphData(
        image=scaled,
        exit_x=exit_x,
        exit_y=exit_y,
        entry_x=entry_x,
        entry_y=entry_y,
        ink_color=avg_color,
        stroke_width=stroke_w,
    )


def _draw_cursive_connector(draw, p0, p1, color, width=2):
    """Рисует плавную каллиграфическую соединительную кривую Безье между двумя буквами."""
    import math

    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]

    if dx < 1:
        return

    # Натуральная форма соединительного штриха: плавный вынос хвоста и подъем к началу буквы
    cx1 = p0[0] + dx * 0.45
    cy1 = p0[1] + (1.5 if dy >= 0 else -1.0)
    cx2 = p0[0] + dx * 0.8
    cy2 = p1[1] + (1.0 if dy < 0 else -1.0)

    steps = max(6, int(math.hypot(dx, dy) * 1.5))
    pts = []
    for i in range(steps + 1):
        t = i / steps
        bx = (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * cx1 + 3 * (1 - t) * t ** 2 * cx2 + t ** 3 * p1[0]
        by = (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * cy1 + 3 * (1 - t) * t ** 2 * cy2 + t ** 3 * p1[1]
        pts.append((bx, by))

    r, g, b = color[:3]
    rgba = (r, g, b, 235)
    line_w = int(round(width))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=rgba, width=line_w)
        half = line_w / 2.0
        draw.ellipse([pts[i][0] - half, pts[i][1] - half, pts[i][0] + half, pts[i][1] + half], fill=rgba)


def _tokenize_word(word, sample_paths):
    """Разбивает слово на фрагменты, находя самые длинные сохраненные связки и буквы."""
    tokens = []
    i = 0
    n = len(word)
    while i < n:
        matched = None
        for length in range(min(12, n - i), 0, -1):
            sub = word[i : i + length]
            if sub in sample_paths or sub.lower() in sample_paths or sub.upper() in sample_paths:
                matched = sub
                break
        if matched:
            tokens.append(matched)
            i += len(matched)
        else:
            tokens.append(word[i])
            i += 1
    return tokens


def render_math_to_image(latex_expr, target_height=58, ink_color=(34, 40, 59), dpi=180):
    """
    Рендерит математическое выражение (формулы высшей математики)
    в прозрачное изображение с рукописным стилем нанесения чернил.
    """
    if not latex_expr:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    expr = latex_expr.strip()
    # Восстанавливаем символы, если строка была передана через сырой парсер
    expr = expr.replace("\x0c", r"\f").replace("\a", r"\a").replace("\b", r"\b")
    if expr.startswith("$$") and expr.endswith("$$") and len(expr) > 4:
        expr = expr[2:-2].strip()
    elif expr.startswith(r"\[") and expr.endswith(r"\]") and len(expr) > 4:
        expr = expr[2:-2].strip()
    elif expr.startswith("$") and expr.endswith("$") and len(expr) > 2:
        expr = expr[1:-1].strip()

    r, g, b = (ink_color[0], ink_color[1], ink_color[2]) if len(ink_color) >= 3 else (34, 40, 59)
    hex_color = f"#{r:02x}{g:02x}{b:02x}"

    img = None
    # 1. Пробуем отрендерить через Mathtext
    try:
        fig = plt.figure(figsize=(0.01, 0.01), dpi=dpi)
        fig.patch.set_alpha(0.0)
        # Оборачиваем в $ для движка mathtext
        fig.text(0.5, 0.5, f"${expr}$", fontsize=20, color=hex_color, ha="center", va="center")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.03, dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        img = Image.open(buf).convert("RGBA")
    except Exception:
        # 2. Если в формуле опечатка или TeX ошибка, рендерим как текст
        try:
            plt.close(fig)
        except Exception:
            pass
        try:
            fig = plt.figure(figsize=(0.01, 0.01), dpi=dpi)
            fig.patch.set_alpha(0.0)
            fig.text(0.5, 0.5, expr, fontsize=16, color=hex_color, ha="center", va="center")
            buf = io.BytesIO()
            fig.savefig(buf, format="png", transparent=True, bbox_inches="tight", pad_inches=0.03, dpi=dpi)
            plt.close(fig)
            buf.seek(0)
            img = Image.open(buf).convert("RGBA")
        except Exception:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    if not img:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    # Органичное масштабирование под высоту строки в тетради
    w, h = img.size
    if h > 0:
        # Для многоэтажных формул (интегралы с пределами, дроби, матрицы) допускаем высоту до 1.4 строки
        scale = max(0.35, min(1.3, (target_height * 1.1) / float(h)))
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Небольшой естественный рукописный микро-наклон
    angle = random.uniform(-0.5, 0.5)
    img = img.rotate(angle, expand=True, resample=Image.BICUBIC)
    return img


def _parse_line_tokens(paragraph):
    """
    Разбивает строку текста на фрагменты: обычные слова и формулы высшей математики
    ($...$, $$...$$, \\[...\\] или чистые LaTeX команды).
    """
    if not paragraph.strip():
        return []

    # Проверяем, является ли весь абзац блочной формулой
    clean_p = paragraph.strip()
    if (clean_p.startswith("$$") and clean_p.endswith("$$")) or (clean_p.startswith(r"\[") and clean_p.endswith(r"\]")):
        return [{"type": "math", "latex": clean_p, "is_block": True}]

    # Проверяем строки, начинающиеся с ключевых математических операторов без $
    if (
        clean_p.startswith(r"\int")
        or clean_p.startswith(r"\lim")
        or clean_p.startswith(r"\sum")
        or clean_p.startswith(r"\frac")
        or clean_p.startswith(r"\begin")
    ):
        return [{"type": "math", "latex": clean_p, "is_block": True}]

    pattern = r"(\$\$.*?\$\$|\\\[.*?\\\]|\$.*?\$)"
    parts = re.split(pattern, paragraph)
    tokens = []
    for part in parts:
        if not part:
            continue
        if (part.startswith("$$") and part.endswith("$$")) or (part.startswith(r"\[") and part.endswith(r"\]")):
            tokens.append({"type": "math", "latex": part, "is_block": True})
        elif part.startswith("$") and part.endswith("$") and len(part) > 2:
            tokens.append({"type": "math", "latex": part, "is_block": False})
        else:
            words = part.split(" ")
            for w in words:
                tokens.append({"type": "word", "text": w})
    return tokens



def render_text_to_pages(
    text,
    sample_paths,
    paper=DEFAULT_PAPER,
    font_size=DEFAULT_FONT_SIZE,
    cursive=True,
    cursive_density="standard",
    cursive_profile=None,
    style=DEFAULT_STYLE,
):
    """Компонует текст из выбранного стиля почерка или личных образцов букв со связками.

    sample_paths: dict, символ/связка -> путь к PNG файлу с образцом.
    paper: ключ варианта бумаги (см. PAPER_STYLES).
    font_size: 'compact', 'standard', 'large' или числовой масштаб (scale).
    cursive: True — слитное рукописное письмо со связками букв, False — раздельные буквы.
    cursive_density: 'tight' (плотные связки), 'standard' (естественные), 'loose' (свободные).
    style: ключ стиля почерка (см. HANDWRITING_STYLES).
    """
    params = get_font_params(font_size)
    scale = params["scale"]
    line_height = params["line_height"]
    line_ascent = params["line_ascent"]
    space_width = params["space_width"]
    margin_x = params["margin_x"]
    margin_top = params["margin_top"]
    margin_bottom = params["margin_bottom"]

    # Настройка межбуквенного интервала для слитного или раздельного письма
    if cursive:
        if cursive_density == "tight":
            letter_gap = max(2, round(scale * 16))
        elif cursive_density == "loose":
            letter_gap = max(4, round(scale * 30))
        else:  # standard
            letter_gap = max(3, round(scale * 23))
    else:
        letter_gap = params["letter_spacing"]

    style_cfg = HANDWRITING_STYLES.get(style) or HANDWRITING_STYLES[DEFAULT_STYLE]
    fallback_font_file = style_cfg.get("font_file", "MarckScript-Regular.ttf")
    fallback_font_path = _find_font_path(fallback_font_file)

    glyph_baseline_offset = round(CANVAS_BASELINE * scale)
    glyph_cache = {}

    def get_glyph(token):
        if token in glyph_cache:
            return glyph_cache[token]

        res = None
        # 1. Если стиль использует образцы пользователя (режим "Мой личный почерк")
        if style_cfg.get("use_samples", True) and sample_paths:
            path = sample_paths.get(token) or sample_paths.get(token.lower()) or sample_paths.get(token.upper())
            if path and os.path.exists(path):
                res = _load_glyph(path, scale=scale)

        # 2. Если образец не найден или выбран конкретный рукописный стиль:
        if res is None and fallback_font_path:
            res = _render_font_glyph(token, fallback_font_path, scale=scale, ink_color=math_ink_color)

        glyph_cache[token] = res
        return res

    def new_blank_page():
        return get_paper_background(
            paper,
            (PAGE_WIDTH, PAGE_HEIGHT),
            line_height=line_height,
            line_ascent=line_ascent,
            margin_top=margin_top,
            margin_x=margin_x,
        ).convert("RGBA")

    pages = []
    page = new_blank_page()
    page_draw = ImageDraw.Draw(page)
    x, y = margin_x, margin_top

    def new_page():
        nonlocal page, page_draw, x, y
        pages.append(page)
        page = new_blank_page()
        page_draw = ImageDraw.Draw(page)
        x, y = margin_x, margin_top

    math_ink_color = (34, 40, 59)
    if cursive_profile and "ink_color" in cursive_profile:
        try:
            math_ink_color = tuple(cursive_profile["ink_color"][:3])
        except Exception:
            pass

    paragraphs = text.replace("\r\n", "\n").split("\n")
    for p_index, paragraph in enumerate(paragraphs):
        line_items = _parse_line_tokens(paragraph)
        if not line_items:
            x = margin_x
            y += line_height
            if y + line_height > PAGE_HEIGHT - margin_bottom:
                new_page()
            continue

        for item_index, item in enumerate(line_items):
            if item["type"] == "math":
                is_block = item.get("is_block", False)
                formula_target_h = int(line_height * 1.35) if is_block else int(line_height * 1.1)
                math_img = render_math_to_image(item["latex"], target_height=formula_target_h, ink_color=math_ink_color)

                # Если это блочная формула (например, $$...$$ или отдельная строка формулы)
                if is_block:
                    if x > margin_x:
                        x = margin_x
                        y += line_height
                        if y + line_height > PAGE_HEIGHT - margin_bottom:
                            new_page()

                    avail_w = PAGE_WIDTH - 2 * margin_x
                    if math_img.width > avail_w:
                        scale_factor = avail_w / float(math_img.width)
                        math_img = math_img.resize((avail_w, max(1, int(math_img.height * scale_factor))), Image.Resampling.LANCZOS)

                    fx = margin_x + max(0, (avail_w - math_img.width) // 2)
                    if y + math_img.height > PAGE_HEIGHT - margin_bottom:
                        new_page()

                    page.alpha_composite(math_img, (fx, y))
                    y += max(line_height, math_img.height + 10)
                    x = margin_x
                    continue

                # Если это инлайн формула ($...$)
                if x + math_img.width > PAGE_WIDTH - margin_x and x > margin_x:
                    x = margin_x
                    y += line_height
                    if y + line_height > PAGE_HEIGHT - margin_bottom:
                        new_page()

                baseline_y = y + line_ascent
                fy = max(y, baseline_y - int(math_img.height * 0.72))
                if y + math_img.height > PAGE_HEIGHT - margin_bottom:
                    new_page()
                    baseline_y = y + line_ascent
                    fy = max(y, baseline_y - int(math_img.height * 0.72))

                page.alpha_composite(math_img, (x, fy))
                x += math_img.width + space_width
                continue

            # Обычное слово
            word = item.get("text", "")
            if not word:
                x += space_width
                continue

            tokens = _tokenize_word(word, sample_paths)

            # Вычисляем общую ширину слова
            word_width = 0
            for idx, tok in enumerate(tokens):
                g = get_glyph(tok)
                if g:
                    word_width += g.width + (letter_gap if idx < len(tokens) - 1 else 0)
                else:
                    word_width += space_width // 2

            # Перенос слова на новую строку, если не помещается
            if x + word_width > PAGE_WIDTH - margin_x and x > margin_x:
                x = margin_x
                y += line_height

            if y + line_height > PAGE_HEIGHT - margin_bottom:
                new_page()

            # Размещаем токены слова
            word_positions = []
            cur_x = x
            baseline_y = y + line_ascent

            for tok in tokens:
                glyph = get_glyph(tok)
                if glyph is None:
                    cur_x += space_width // 2
                    continue

                gw = glyph.width
                if cur_x + gw > PAGE_WIDTH - margin_x and cur_x > margin_x:
                    cur_x = margin_x
                    y += line_height
                    baseline_y = y + line_ascent
                    if y + line_height > PAGE_HEIGHT - margin_bottom:
                        new_page()
                        baseline_y = y + line_ascent

                angle = random.uniform(-0.8, 0.8)
                glyph_r = glyph.image.rotate(angle, expand=True, resample=Image.BICUBIC)

                offset_x = cur_x
                offset_y = baseline_y - glyph_baseline_offset + random.choice([-1, 0, 1])

                word_positions.append(
                    {
                        "token": tok,
                        "glyph": glyph,
                        "rotated": glyph_r,
                        "x": offset_x,
                        "y": offset_y,
                        "width": gw,
                    }
                )
                cur_x += gw + letter_gap

            # Если включен слитный режим, рисуем соединительные связки между соседними буквами слова
            if cursive and len(word_positions) > 1:
                for i in range(len(word_positions) - 1):
                    item1 = word_positions[i]
                    item2 = word_positions[i + 1]
                    tok1 = item1["token"]
                    tok2 = item2["token"]

                    # Связываем только буквы (не знаки препинания и не цифры)
                    if any(c.isalpha() for c in tok1) and any(c.isalpha() for c in tok2):
                        g1 = item1["glyph"]
                        g2 = item2["glyph"]
                        p0 = (item1["x"] + g1.exit_x, item1["y"] + g1.exit_y)
                        p1 = (item2["x"] + g2.entry_x, item2["y"] + g2.entry_y)
                        conn_width = g1.stroke_width
                        _draw_cursive_connector(page_draw, p0, p1, g1.ink_color, width=conn_width)

            # Накладываем сами символы
            for itm in word_positions:
                page.alpha_composite(itm["rotated"], (itm["x"], itm["y"]))

            x = cur_x
            if item_index != len(line_items) - 1:
                x += space_width

        # Переход на новую строку после абзаца
        if p_index != len(paragraphs) - 1:
            x = margin_x
            y += line_height
            if y + line_height > PAGE_HEIGHT - margin_bottom:
                new_page()

    pages.append(page)
    return [pg.convert("RGB") for pg in pages]



def save_png(pages, png_path):
    """Сохраняет страницы друг под другом в одну длинную PNG-картинку (удобно для предпросмотра)."""
    if len(pages) == 1:
        pages[0].save(png_path)
        return
    total_height = sum(p.height for p in pages) + 20 * (len(pages) - 1)
    combined = Image.new("RGB", (pages[0].width, total_height), (240, 240, 240))
    y = 0
    for p in pages:
        combined.paste(p, (0, y))
        y += p.height + 20
    combined.save(png_path)


def save_pdf(pages, pdf_path):
    first, rest = pages[0], pages[1:]
    if rest:
        first.save(pdf_path, "PDF", resolution=150.0, save_all=True, append_images=rest)
    else:
        first.save(pdf_path, "PDF", resolution=150.0)
