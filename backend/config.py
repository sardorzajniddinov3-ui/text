import os

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # Секретный ключ для сессий/cookie
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # База данных (из переменной окружения DATABASE_URL или локальная SQLite)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'handwriting.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Папки для файлов
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads"))
    GENERATED_FOLDER = os.environ.get("GENERATED_FOLDER", os.path.join(BASE_DIR, "generated"))

    # Ключ Google Cloud Vision API
    GOOGLE_VISION_API_KEY = os.environ.get("GOOGLE_VISION_API_KEY", "")

    # Supabase (только из переменных окружения)
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


    # Ограничение на размер загружаемого фото (10 МБ)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # Cookie сессии
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_HTTPONLY = True
