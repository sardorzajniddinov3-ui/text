import base64

import requests
from flask import current_app

VISION_URL = "https://vision.googleapis.com/v1/images:annotate"


class OcrError(Exception):
    pass


def recognize_text_from_image(image_bytes: bytes) -> str:
    """Отправляет фото в Google Cloud Vision API и возвращает распознанный текст.

    Требует переменную окружения GOOGLE_VISION_API_KEY (см. README.md - как её получить).
    """
    api_key = current_app.config.get("GOOGLE_VISION_API_KEY")
    if not api_key:
        raise OcrError(
            "OCR не настроен: задайте переменную окружения GOOGLE_VISION_API_KEY "
            "(см. README.md, раздел 'Настройка OCR')."
        )

    payload = {
        "requests": [
            {
                "image": {"content": base64.b64encode(image_bytes).decode("utf-8")},
                "features": [{"type": "TEXT_DETECTION"}],
                "imageContext": {"languageHints": ["ru", "en"]},
            }
        ]
    }

    try:
        resp = requests.post(f"{VISION_URL}?key={api_key}", json=payload, timeout=30)
    except requests.RequestException as exc:
        raise OcrError(f"Не удалось обратиться к сервису OCR: {exc}") from exc

    if resp.status_code != 200:
        raise OcrError(f"Сервис OCR вернул ошибку ({resp.status_code}): {resp.text[:300]}")

    data = resp.json()
    responses = data.get("responses") or [{}]
    first = responses[0]

    if "error" in first:
        raise OcrError(f"Ошибка Google Vision: {first['error'].get('message', 'неизвестная ошибка')}")

    annotation = first.get("fullTextAnnotation")
    if annotation and annotation.get("text"):
        return annotation["text"].strip()

    return ""
