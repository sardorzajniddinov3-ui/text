import base64
import os
import uuid

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from alphabet import ALPHABET, GROUPS
from models import LetterSample, db

samples_bp = Blueprint("samples", __name__, url_prefix="/api/samples")


@samples_bp.get("/alphabet")
def get_alphabet():
    return jsonify(alphabet=ALPHABET, groups=GROUPS)


@samples_bp.get("/progress")
@login_required
def progress():
    done = [s.char for s in current_user.samples]
    return jsonify(done=done, total=len(ALPHABET))


@samples_bp.post("")
@login_required
def save_sample():
    data = request.get_json(force=True, silent=True) or {}
    char = data.get("char")
    image_data_url = data.get("image")

    if char not in ALPHABET:
        return jsonify(error="Неизвестный символ"), 400
    if not image_data_url:
        return jsonify(error="Нет изображения"), 400

    if "," in image_data_url:
        image_data_url = image_data_url.split(",", 1)[1]

    try:
        raw = base64.b64decode(image_data_url)
    except Exception:
        return jsonify(error="Не удалось прочитать изображение"), 400

    user_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], str(current_user.id))
    os.makedirs(user_folder, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    path = os.path.join(user_folder, filename)
    with open(path, "wb") as f:
        f.write(raw)

    existing = LetterSample.query.filter_by(user_id=current_user.id, char=char).first()
    if existing:
        old_path = existing.file_path
        existing.file_path = path
        db.session.commit()
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
    else:
        db.session.add(LetterSample(user_id=current_user.id, char=char, file_path=path))
        db.session.commit()

    return jsonify(ok=True, char=char)


@samples_bp.delete("/<char>")
@login_required
def delete_sample(char):
    existing = LetterSample.query.filter_by(user_id=current_user.id, char=char).first()
    if not existing:
        return jsonify(error="Образец не найден"), 404
    path = existing.file_path
    db.session.delete(existing)
    db.session.commit()
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    return jsonify(ok=True)
