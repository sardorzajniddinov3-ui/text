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


@auth_bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify(error="Неверное имя пользователя или пароль"), 401

    login_user(user, remember=True)
    return jsonify(id=user.id, username=user.username)


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify(ok=True)


@auth_bp.get("/me")
def me():
    if current_user.is_authenticated:
        return jsonify(id=current_user.id, username=current_user.username)
    return jsonify(None)
