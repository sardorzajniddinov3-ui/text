import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageOps

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


def _load_glyph(path, scale=0.21):
    """Загружает сохранённый образец буквы, обрезает поля по бокам и масштабирует.

    Обрезает только по горизонтали, сохраняя полную высоту холста (260px).
    Это обеспечивает правильную посадку букв на строку без искажения высоты.
    """
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
    return cropped.resize((new_w, new_h), Image.LANCZOS)


def render_text_to_pages(text, sample_paths, paper=DEFAULT_PAPER, font_size=DEFAULT_FONT_SIZE):
    """Компонует текст из образцов букв пользователя с чётким, легко читаемым видом.

    sample_paths: dict, символ -> путь к PNG файлу с образцом.
    paper: ключ варианта бумаги (см. PAPER_STYLES).
    font_size: 'compact', 'standard', 'large' или числовой масштаб (scale).
    Возвращает список PIL.Image (по одному на страницу А4), готовых к сохранению.
    """
    params = get_font_params(font_size)
    scale = params["scale"]
    line_height = params["line_height"]
    line_ascent = params["line_ascent"]
    space_width = params["space_width"]
    letter_spacing = params["letter_spacing"]
    margin_x = params["margin_x"]
    margin_top = params["margin_top"]
    margin_bottom = params["margin_bottom"]

    glyph_baseline_offset = round(CANVAS_BASELINE * scale)
    glyph_cache = {}

    def get_glyph(ch):
        if ch in glyph_cache:
            return glyph_cache[ch]
        path = sample_paths.get(ch) or sample_paths.get(ch.lower()) or sample_paths.get(ch.upper())
        res = _load_glyph(path, scale=scale) if path and os.path.exists(path) else None
        glyph_cache[ch] = res
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
    x, y = margin_x, margin_top

    def new_page():
        nonlocal page, x, y
        pages.append(page)
        page = new_blank_page()
        x, y = margin_x, margin_top

    paragraphs = text.replace("\r\n", "\n").split("\n")
    for p_index, paragraph in enumerate(paragraphs):
        words = paragraph.split(" ")
        for w_index, word in enumerate(words):
            # Посчитать ширину слова с учётом чистого межбуквенного интервала
            word_width = 0
            for idx, ch in enumerate(word):
                g = get_glyph(ch)
                if g:
                    word_width += g.size[0] + (letter_spacing if idx < len(word) - 1 else 0)
                else:
                    word_width += space_width

            if x + word_width > PAGE_WIDTH - margin_x and x > margin_x:
                x = margin_x
                y += line_height

            if y + line_height > PAGE_HEIGHT - margin_bottom:
                new_page()

            for ch_idx, ch in enumerate(word):
                glyph = get_glyph(ch)
                if glyph is None:
                    x += space_width
                    continue

                gw = glyph.size[0]
                if x + gw > PAGE_WIDTH - margin_x:
                    x = margin_x
                    y += line_height
                    if y + line_height > PAGE_HEIGHT - margin_bottom:
                        new_page()

                # Мягкий естественный наклон без резких перекосов
                angle = random.uniform(-1.0, 1.0)
                glyph_r = glyph.rotate(angle, expand=True, resample=Image.BICUBIC)

                baseline_y = y + line_ascent
                offset_x = x
                offset_y = baseline_y - glyph_baseline_offset + random.choice([-1, 0, 1])

                page.alpha_composite(glyph_r, (offset_x, offset_y))
                x += gw + letter_spacing

            if w_index != len(words) - 1:
                x += space_width

        # новый абзац -> новая строка
        if p_index != len(paragraphs) - 1:
            x = margin_x
            y += line_height
            if y + line_height > PAGE_HEIGHT - margin_bottom:
                new_page()

    pages.append(page)

    # Убираем альфа-канал
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
