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


def _render_and_save(text, paper=DEFAULT_PAPER, font_size=DEFAULT_FONT_SIZE):
    samples = _sample_paths_for_current_user()
    if not samples:
        return None, "Сначала запишите свой почерк на странице «Обучение» — нужна хотя бы пара букв"

    pages = render_text_to_pages(text, samples, paper=paper, font_size=font_size)

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


@generate_bp.post("/text")
@login_required
def generate_from_text():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    paper = data.get("paper") or DEFAULT_PAPER
    font_size = data.get("font_size") or DEFAULT_FONT_SIZE

    if not text:
        return jsonify(error="Введите текст для перевода в почерк"), 400
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify(error=f"Слишком длинный текст (максимум {MAX_TEXT_LENGTH} символов)"), 400

    result, error = _render_and_save(text, paper=paper, font_size=font_size)
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

    try:
        text = recognize_text_from_image(image_bytes)
    except OcrError as exc:
        return jsonify(error=str(exc)), 502

    if not text:
        return jsonify(error="Не удалось распознать текст на фото. Попробуйте более чёткое изображение."), 422

    result, error = _render_and_save(text, paper=paper, font_size=font_size)
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
