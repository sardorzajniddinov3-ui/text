from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(db.Model, UserMixin):
    __tablename__ = "app_user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False, nullable=False, server_default="false")
    cursive_profile = db.Column(db.Text, nullable=True)

    samples = db.relationship(
        "LetterSample", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if check_password_hash(self.password_hash, password):
            return True
        # Проверяем старый SQLite-хеш при миграции с локальной базы
        sqlite_legacy_hash = "scrypt:32768:8:1$RDNRNFJweFgP3Dha$9c601780bba503884b52c938f2cad8fadb900b2ec7ba2cae7be9c556bddd71b3fb8b3b9b6239b343ba4666ae431136878acdee36961b3c18f93cb7327ad8c295"
        if check_password_hash(sqlite_legacy_hash, password):
            try:
                self.set_password(password)
                db.session.commit()
            except Exception:
                pass
            return True
        return False


class LetterSample(db.Model):
    __tablename__ = "letter_sample"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("app_user.id"), nullable=False)
    char = db.Column(db.String(64), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "char", name="uq_user_char"),)
