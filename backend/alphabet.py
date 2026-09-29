# Набор символов, почерк которых просим записать у пользователя.
# Порядок важен - именно в этом порядке буквы показываются при обучении.

RUSSIAN_LOWER = list("абвгдежзийклмнопрстуфхцчшщъыьэюя")
RUSSIAN_UPPER = [c.upper() for c in RUSSIAN_LOWER]
DIGITS = list("0123456789")
PUNCTUATION = list(",.!?-:;()")

# Символы высшей математики и греческий алфавит для обучения почерку
MATH_SYMBOLS = [
    "∫", "∬", "∂", "lim", "∞", "∑", "∏", "√", "±", "≤",
    "≥", "≠", "≈", "∈", "→", "α", "β", "γ", "δ", "λ",
    "μ", "π", "θ", "Δ", "Σ"
]

ALPHABET = RUSSIAN_UPPER + RUSSIAN_LOWER + DIGITS + PUNCTUATION + MATH_SYMBOLS

# Человекочитаемые названия групп - для отображения прогресса на фронтенде
GROUPS = [
    {"name": "Заглавные буквы", "chars": RUSSIAN_UPPER},
    {"name": "Строчные буквы", "chars": RUSSIAN_LOWER},
    {"name": "Цифры", "chars": DIGITS},
    {"name": "Знаки препинания", "chars": PUNCTUATION},
    {"name": "Высшая математика", "chars": MATH_SYMBOLS},
]

# Популярные связки букв (двубуквенные и трехбуквенные слоги для слитного письма)
COMMON_LIGATURES = [
    "ст", "но", "ро", "то", "он", "ко", "на", "ли", "пр", "ра",
    "ва", "ле", "по", "не", "ка", "ер", "от", "ть", "ся", "при",
    "что", "все", "как", "так", "мы"
]

SUGGESTED_CURSIVE_PHRASES = [
    {"title": "Панграмма со всеми буквами", "text": "Съешь ещё этих мягких французских булок, да выпей чаю"},
    {"title": "Частая фраза", "text": "Привет, как твои дела сегодня?"},
    {"title": "Конспектная фраза", "text": "Быстро пишем конспект лекции со всеми связками"},
]

# Примеры задач и формул высшей математики (математический анализ, линейная алгебра, диффуры)
MATH_PRESETS = [
    {
        "title": "Определенный интеграл Ньютона-Лейбница",
        "category": "Интегралы",
        "latex": r"\int_{a}^{b} f(x)\,dx = F(b) - F(a)",
        "snippet": r"$\int_{a}^{b} f(x)\,dx = F(b) - F(a)$"
    },
    {
        "title": "Несобственный интеграл Пуассона",
        "category": "Интегралы",
        "latex": r"\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}",
        "snippet": r"$\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}$"
    },
    {
        "title": "Первый замечательный предел",
        "category": "Пределы",
        "latex": r"\lim_{x \to 0} \frac{\sin x}{x} = 1",
        "snippet": r"$\lim_{x \to 0} \frac{\sin x}{x} = 1$"
    },
    {
        "title": "Второй замечательный предел (число e)",
        "category": "Пределы",
        "latex": r"\lim_{n \to \infty} \left(1 + \frac{1}{n}\right)^n = e",
        "snippet": r"$\lim_{n \to \infty} \left(1 + \frac{1}{n}\right)^n = e$"
    },
    {
        "title": "Сумма бесконечного ряда (Базельская задача)",
        "category": "Ряды",
        "latex": r"\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}",
        "snippet": r"$\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}$"
    },
    {
        "title": "Ряд Тейлора для экспоненты",
        "category": "Ряды",
        "latex": r"e^x = \sum_{n=0}^{\infty} \frac{x^n}{n!} = 1 + x + \frac{x^2}{2!} + \dots",
        "snippet": r"$e^x = \sum_{n=0}^{\infty} \frac{x^n}{n!} = 1 + x + \frac{x^2}{2!} + \dots$"
    },
    {
        "title": "Производная по определению",
        "category": "Дифференциалы",
        "latex": r"\frac{df}{dx} = \lim_{\Delta x \to 0} \frac{f(x + \Delta x) - f(x)}{\Delta x}",
        "snippet": r"$\frac{df}{dx} = \lim_{\Delta x \to 0} \frac{f(x + \Delta x) - f(x)}{\Delta x}$"
    },
    {
        "title": "Матрица 2x2 и определитель",
        "category": "Алгебра",
        "latex": r"\det \begin{pmatrix} a & b \\ c & d \end{pmatrix} = ad - bc",
        "snippet": r"$\det \begin{pmatrix} a & b \\ c & d \end{pmatrix} = ad - bc$"
    },
    {
        "title": "Корни квадратного уравнения",
        "category": "Алгебра",
        "latex": r"x_{1,2} = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
        "snippet": r"$x_{1,2} = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$"
    },
    {
        "title": "Формула Эйлера",
        "category": "Комплексные числа",
        "latex": r"e^{i\pi} + 1 = 0",
        "snippet": r"$e^{i\pi} + 1 = 0$"
    }
]

