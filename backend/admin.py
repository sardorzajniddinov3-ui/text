from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import current_user

from models import LetterSample, User, db

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify(error="Требуется авторизация"), 401
        if not current_user.is_admin:
            return jsonify(error="Доступ запрещён"), 403
        return f(*args, **kwargs)
    return decorated


@admin_bp.get("/stats")
@admin_required
def stats():
    total_users = User.query.count()
    total_samples = LetterSample.query.count()
    admin_users = User.query.filter_by(is_admin=True).count()
    return jsonify(
        total_users=total_users,
        total_samples=total_samples,
        admin_users=admin_users,
    )


@admin_bp.get("/users")
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        sample_count = LetterSample.query.filter_by(user_id=u.id).count()
        result.append({
            "id": u.id,
            "username": u.username,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "sample_count": sample_count,
        })
    return jsonify(users=result)


@admin_bp.delete("/users/<int:user_id>")
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        return jsonify(error="Нельзя удалить самого себя"), 400
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify(ok=True)


@admin_bp.post("/users/<int:user_id>/toggle-admin")
@admin_required
def toggle_admin(user_id):
    if user_id == current_user.id:
        return jsonify(error="Нельзя изменить собственные права"), 400
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    return jsonify(ok=True, is_admin=user.is_admin)


@admin_bp.get("/users/<int:user_id>/samples")
@admin_required
def user_samples(user_id):
    user = User.query.get_or_404(user_id)
    samples = LetterSample.query.filter_by(user_id=user_id).order_by(LetterSample.char).all()
    return jsonify(
        username=user.username,
        samples=[{"id": s.id, "char": s.char, "created_at": s.created_at.isoformat() if s.created_at else None} for s in samples]
    )


@admin_bp.delete("/users/<int:user_id>/samples")
@admin_required
def clear_user_samples(user_id):
    LetterSample.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify(ok=True)
