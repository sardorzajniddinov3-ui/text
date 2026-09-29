import base64
import json
import os
import uuid
from datetime import datetime
from PIL import Image
import io

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from alphabet import ALPHABET, GROUPS, COMMON_LIGATURES, SUGGESTED_CURSIVE_PHRASES
from models import LetterSample, User, db

samples_bp = Blueprint("samples", __name__, url_prefix="/api/samples")


def _analyze_cursive_sample(raw_bytes):
    """Анализирует написанный от руки текст и извлекает каллиграфические параметры связок."""
    try:
        im = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
        bbox = im.getbbox()
        if not bbox:
            return {"enabled": True, "density": "standard", "stroke_width": 2, "ink_color": [34, 40, 59]}

        # Собираем чернильные пиксели
        w, h = im.size
        ink_pixels = []
        ink_colors = []
        for x in range(bbox[0], bbox[2], 2):
            col_ink = 0
            for y in range(bbox[1], bbox[3]):
                r, g, b, a = im.getpixel((x, y))
                if a > 80:
                    col_ink += 1
                    ink_pixels.append((x, y))
                    if a > 180:
                        ink_colors.append((r, g, b))

        # Оценка цвета чернил
        if ink_colors:
            avg_r = round(sum(c[0] for c in ink_colors) / len(ink_colors))
            avg_g = round(sum(c[1] for c in ink_colors) / len(ink_colors))
            avg_b = round(sum(c[2] for c in ink_colors) / len(ink_colors))
            color = [avg_r, avg_g, avg_b]
        else:
            color = [34, 40, 59]

        # Оценка высоты соединения букв относительно холста (baseline ~ 180)
        baseline_y = 180
        if ink_pixels:
            y_coords = [p[1] for p in ink_pixels]
            # медиана нижней трети
            sorted_y = sorted(y_coords)
            baseline_estimate = sorted_y[int(len(sorted_y) * 0.75)]
        else:
            baseline_estimate = 180

        return {
            "enabled": True,
            "density": "standard",
            "stroke_width": 2,
            "ink_color": color,
            "baseline_y": baseline_estimate,
            "curvature": 0.5,
            "updated_at": datetime.utcnow().isoformat(),
        }
    except Exception:
        return {"enabled": True, "density": "standard", "stroke_width": 2, "ink_color": [34, 40, 59]}


@samples_bp.get("/alphabet")
def get_alphabet():
    return jsonify(alphabet=ALPHABET, groups=GROUPS)


@samples_bp.get("/progress")
@login_required
def progress():
    all_samples = current_user.samples
    done_chars = [s.char for s in all_samples if len(s.char) == 1]
    done_ligatures = [s.char for s in all_samples if len(s.char) > 1]
    return jsonify(
        done=done_chars,
        total=len(ALPHABET),
        done_ligatures=done_ligatures,
        ligatures_total=len(COMMON_LIGATURES),
    )


@samples_bp.get("/cursive-presets")
@login_required
def get_cursive_presets():
    user_ligatures = [s.char for s in current_user.samples if len(s.char) > 1]
    profile = {}
    if current_user.cursive_profile:
        try:
            profile = json.loads(current_user.cursive_profile)
        except Exception:
            pass

    return jsonify(
        common_ligatures=COMMON_LIGATURES,
        phrases=SUGGESTED_CURSIVE_PHRASES,
        user_ligatures=user_ligatures,
        cursive_profile=profile,
    )


@samples_bp.get("/cursive-profile")
@login_required
def get_cursive_profile():
    profile = {"enabled": True, "density": "standard", "stroke_width": 2, "ink_color": [34, 40, 59]}
    if current_user.cursive_profile:
        try:
            profile.update(json.loads(current_user.cursive_profile))
        except Exception:
            pass
    return jsonify(profile=profile)


@samples_bp.post("/cursive-profile")
@login_required
def update_cursive_profile():
    data = request.get_json(force=True, silent=True) or {}
    profile = {}
    if current_user.cursive_profile:
        try:
            profile = json.loads(current_user.cursive_profile)
        except Exception:
            pass
    profile.update(data)
    current_user.cursive_profile = json.dumps(profile, ensure_ascii=False)
    db.session.commit()
    return jsonify(ok=True, profile=profile)


@samples_bp.post("")
@login_required
def save_sample():
    data = request.get_json(force=True, silent=True) or {}
    char = (data.get("char") or "").strip()
    image_data_url = data.get("image")
    is_cursive_sample = bool(data.get("is_cursive"))

    if not char:
        return jsonify(error="Символ или связка не могут быть пустыми"), 400
    if len(char) > 64:
        return jsonify(error="Слишком длинная строка (максимум 64 символа)"), 400
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

    # Если образец записан в режиме слитного текста или связки,
    # обновляем профиль слитных связок пользователя:
    learned_profile = None
    if is_cursive_sample or len(char) > 1:
        learned_profile = _analyze_cursive_sample(raw)
        # Сохраняем в профиль пользователя
        profile = {}
        if current_user.cursive_profile:
            try:
                profile = json.loads(current_user.cursive_profile)
            except Exception:
                pass
        profile.update(learned_profile)
        current_user.cursive_profile = json.dumps(profile, ensure_ascii=False)
        db.session.commit()

    return jsonify(ok=True, char=char, cursive_profile=learned_profile)


@samples_bp.delete("/<path:char>")
@login_required
def delete_sample(char):
    char = char.strip()
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
    return jsonify(ok=True, char=char)
