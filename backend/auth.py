from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from models import User, db

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if len(username) < 3:
        return jsonify(error="Имя пользователя должно быть не короче 3 символов"), 400
    if len(password) < 6:
        return jsonify(error="Пароль должен быть не короче 6 символов"), 400
    if User.query.filter_by(username=username).first():
        return jsonify(error="Пользователь с таким именем уже существует"), 409

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user, remember=True)
    return jsonify(id=user.id, username=user.username), 201


def _find_user(username: str):
    """Ищет пользователя с гибким сопоставлением (без учета регистра и домена @gmail.com)."""
    if not username:
        return None
    clean = username.strip()
    # 1. Точное совпадение
    u = User.query.filter_by(username=clean).first()
    if u:
        return u
    # 2. Без учёта регистра
    u = User.query.filter(db.func.lower(User.username) == clean.lower()).first()
    if u:
        return u
    # 3. Если введено без @gmail.com
    if "@" not in clean:
        u = User.query.filter(db.func.lower(User.username) == f"{clean.lower()}@gmail.com").first()
        if u:
            return u
        u = User.query.filter(User.username.ilike(f"{clean}@%")).first()
        if u:
            return u
    return None


@auth_bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify(error="Введите имя пользователя и пароль"), 400

    user = _find_user(username)
    if not user:
        return jsonify(error="Пользователь не найден. Проверьте правильность логина или зарегистрируйтесь"), 401

    if not user.check_password(password):
        return jsonify(error="Неверный пароль. Если забыли пароль — воспользуйтесь кнопкой «Сбросить пароль»"), 401

    login_user(user, remember=True)
    return jsonify(id=user.id, username=user.username)


@auth_bp.post("/reset-password")
def reset_password():
    """Позволяет сбросить/задать новый пароль для своего аккаунта."""
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    new_password = data.get("password") or ""

    if not username:
        return jsonify(error="Укажите имя пользователя"), 400
    if len(new_password) < 6:
        return jsonify(error="Новый пароль должен быть не короче 6 символов"), 400

    user = _find_user(username)
    if not user:
        return jsonify(error="Пользователь с таким именем не найден"), 404

    user.set_password(new_password)
    db.session.commit()

    login_user(user, remember=True)
    return jsonify(ok=True, id=user.id, username=user.username)


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify(ok=True)


@auth_bp.get("/me")
def me():
    if current_user.is_authenticated:
        return jsonify(id=current_user.id, username=current_user.username, is_admin=current_user.is_admin)
    return jsonify(None)
