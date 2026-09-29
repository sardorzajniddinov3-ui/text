import os
import uuid

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_login import current_user, login_required

from ocr import OcrError, recognize_text_from_image
from render import (
    DEFAULT_FONT_SIZE,
    DEFAULT_PAPER,
    list_font_sizes,
    list_paper_styles,
    render_text_to_pages,
    save_pdf,
    save_png,
)

generate_bp = Blueprint("generate", __name__, url_prefix="/api/generate")

MAX_TEXT_LENGTH = 10000


def _sample_paths_for_current_user():
    return {s.char: s.file_path for s in current_user.samples}


import json

def _render_and_save(
    text,
    paper=DEFAULT_PAPER,
    font_size=DEFAULT_FONT_SIZE,
    cursive=True,
    cursive_density="standard",
):
    samples = _sample_paths_for_current_user()
    if not samples:
        return None, "Сначала запишите свой почерк на странице «Обучение» — нужна хотя бы пара букв"

    profile = None
    if getattr(current_user, "cursive_profile", None):
        try:
            profile = json.loads(current_user.cursive_profile)
        except Exception:
            pass

    pages = render_text_to_pages(
        text,
        samples,
        paper=paper,
        font_size=font_size,
        cursive=cursive,
        cursive_density=cursive_density,
        cursive_profile=profile,
    )

    folder = os.path.join(current_app.config["GENERATED_FOLDER"], str(current_user.id))
    os.makedirs(folder, exist_ok=True)
    file_id = uuid.uuid4().hex
    png_path = os.path.join(folder, f"{file_id}.png")
    pdf_path = os.path.join(folder, f"{file_id}.pdf")

    save_png(pages, png_path)
    save_pdf(pages, pdf_path)

    return {
        "id": file_id,
        "png_url": f"/api/generate/download/{file_id}.png",
        "pdf_url": f"/api/generate/download/{file_id}.pdf",
    }, None


@generate_bp.get("/papers")
def get_papers():
    return jsonify(
        papers=list_paper_styles(),
        default=DEFAULT_PAPER,
        font_sizes=list_font_sizes(),
        default_font_size=DEFAULT_FONT_SIZE,
    )


@generate_bp.post("/preview")
@login_required
def generate_preview():
    """Быстрый предпросмотр слитного почерка в виде base64 data-URL для вкладки связок."""
    import base64
    import io

    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "Привет, как дела? Мой слитный почерк.").strip()
    cursive = data.get("cursive", True)
    cursive_density = data.get("cursive_density") or "standard"
    font_size = data.get("font_size") or DEFAULT_FONT_SIZE

    samples = _sample_paths_for_current_user()
    if not samples:
        return jsonify(error="Пока нет сохранённых образцов букв"), 400

    profile = None
    if getattr(current_user, "cursive_profile", None):
        try:
            profile = json.loads(current_user.cursive_profile)
        except Exception:
            pass

    pages = render_text_to_pages(
        text,
        samples,
        paper="blank",
        font_size=font_size,
        cursive=cursive,
        cursive_density=cursive_density,
        cursive_profile=profile,
    )

    buf = io.BytesIO()
    # Берем первую страницу и кадрируем по высоте содержимого для компактного предпросмотра
    first_page = pages[0]
    first_page.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return jsonify(data_url=f"data:image/png;base64,{b64}")


@generate_bp.post("/text")
@login_required
def generate_from_text():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    paper = data.get("paper") or DEFAULT_PAPER
    font_size = data.get("font_size") or DEFAULT_FONT_SIZE
    cursive = data.get("cursive", True)
    if isinstance(cursive, str):
        cursive = cursive.lower() in ("true", "1", "yes")
    cursive_density = data.get("cursive_density") or "standard"

    if not text:
        return jsonify(error="Введите текст для перевода в почерк"), 400
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify(error=f"Слишком длинный текст (максимум {MAX_TEXT_LENGTH} символов)"), 400

    result, error = _render_and_save(
        text,
        paper=paper,
        font_size=font_size,
        cursive=cursive,
        cursive_density=cursive_density,
    )
    if error:
        return jsonify(error=error), 400
    return jsonify(result)


@generate_bp.post("/photo")
@login_required
def generate_from_photo():
    if "photo" not in request.files:
        return jsonify(error="Файл не найден"), 400

    file = request.files["photo"]
    image_bytes = file.read()
    if not image_bytes:
        return jsonify(error="Пустой файл"), 400

    paper = request.form.get("paper") or DEFAULT_PAPER
    font_size = request.form.get("font_size") or DEFAULT_FONT_SIZE
    cursive_val = request.form.get("cursive", "true")
    cursive = cursive_val.lower() in ("true", "1", "yes")
    cursive_density = request.form.get("cursive_density") or "standard"

    try:
        text = recognize_text_from_image(image_bytes)
    except OcrError as exc:
        return jsonify(error=str(exc)), 502

    if not text:
        return jsonify(error="Не удалось распознать текст на фото. Попробуйте более чёткое изображение."), 422

    result, error = _render_and_save(
        text,
        paper=paper,
        font_size=font_size,
        cursive=cursive,
        cursive_density=cursive_density,
    )
    if error:
        return jsonify(error=error), 400

    result["recognized_text"] = text
    return jsonify(result)


@generate_bp.get("/download/<filename>")
@login_required
def download(filename):
    if "/" in filename or ".." in filename:
        return jsonify(error="Некорректное имя файла"), 400
    folder = os.path.join(current_app.config["GENERATED_FOLDER"], str(current_user.id))
    return send_from_directory(folder, filename)


@generate_bp.get("/math-presets")
def get_math_presets():
    """Возвращает популярные формулы и шаблоны высшей математики."""
    from alphabet import MATH_PRESETS, MATH_SYMBOLS
    return jsonify(presets=MATH_PRESETS, symbols=MATH_SYMBOLS)


@generate_bp.post("/math-preview")
def math_preview():
    """Генерирует мгновенный рукописный предпросмотр введенной математической формулы."""
    data = request.get_json(force=True, silent=True) or {}
    formula = (data.get("formula") or "").strip()
    if not formula:
        return jsonify(error="Формула не указана"), 400

    ink_color = (34, 40, 59)
    if current_user.is_authenticated and getattr(current_user, "cursive_profile", None):
        try:
            prof = json.loads(current_user.cursive_profile)
            if "ink_color" in prof and len(prof["ink_color"]) >= 3:
                ink_color = tuple(prof["ink_color"][:3])
        except Exception:
            pass

    import base64
    import io
    from render import render_math_to_image

    img = render_math_to_image(formula, target_height=65, ink_color=ink_color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return jsonify(ok=True, image=f"data:image/png;base64,{b64}")

