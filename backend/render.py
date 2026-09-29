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


def render_text_to_pages(
    text,
    sample_paths,
    paper=DEFAULT_PAPER,
    font_size=DEFAULT_FONT_SIZE,
    cursive=True,
    cursive_density="standard",
    cursive_profile=None,
):
    """Компонует текст из образцов букв пользователя со слитными связками или раздельно.

    sample_paths: dict, символ/связка -> путь к PNG файлу с образцом.
    paper: ключ варианта бумаги (см. PAPER_STYLES).
    font_size: 'compact', 'standard', 'large' или числовой масштаб (scale).
    cursive: True — слитное рукописное письмо со связками букв, False — раздельные буквы.
    cursive_density: 'tight' (плотные связки), 'standard' (естественные), 'loose' (свободные).
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

    glyph_baseline_offset = round(CANVAS_BASELINE * scale)
    glyph_cache = {}

    def get_glyph(token):
        if token in glyph_cache:
            return glyph_cache[token]
        path = sample_paths.get(token) or sample_paths.get(token.lower()) or sample_paths.get(token.upper())
        res = _load_glyph(path, scale=scale) if path and os.path.exists(path) else None
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

    paragraphs = text.replace("\r\n", "\n").split("\n")
    for p_index, paragraph in enumerate(paragraphs):
        words = paragraph.split(" ")
        for w_index, word in enumerate(words):
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
            for item in word_positions:
                page.alpha_composite(item["rotated"], (item["x"], item["y"]))

            x = cur_x
            if w_index != len(words) - 1:
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
