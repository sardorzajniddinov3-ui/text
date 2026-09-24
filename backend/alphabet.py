# Набор символов, почерк которых просим записать у пользователя.
# Порядок важен - именно в этом порядке буквы показываются при обучении.

RUSSIAN_LOWER = list("абвгдежзийклмнопрстуфхцчшщъыьэюя")
RUSSIAN_UPPER = [c.upper() for c in RUSSIAN_LOWER]
DIGITS = list("0123456789")
PUNCTUATION = list(",.!?-:;()")

ALPHABET = RUSSIAN_UPPER + RUSSIAN_LOWER + DIGITS + PUNCTUATION

# Человекочитаемые названия групп - для отображения прогресса на фронтенде
GROUPS = [
    {"name": "Заглавные буквы", "chars": RUSSIAN_UPPER},
    {"name": "Строчные буквы", "chars": RUSSIAN_LOWER},
    {"name": "Цифры", "chars": DIGITS},
    {"name": "Знаки препинания", "chars": PUNCTUATION},
]
