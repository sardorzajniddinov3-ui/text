(() => {
  "use strict";

  // ---------- DOM refs ----------
  const authView = document.getElementById("auth-view");
  const appView = document.getElementById("app-view");
  const userBox = document.getElementById("user-box");
  const usernameLabel = document.getElementById("username-label");
  const logoutBtn = document.getElementById("logout-btn");

  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const loginError = document.getElementById("login-error");
  const registerError = document.getElementById("register-error");

  const trainView = document.getElementById("train-view");
  const generateView = document.getElementById("generate-view");

  const progressFill = document.getElementById("progress-fill");
  const progressLabel = document.getElementById("progress-label");
  const guideCanvas = document.getElementById("guide-canvas");
  const drawCanvas = document.getElementById("draw-canvas");
  const clearBtn = document.getElementById("clear-btn");
  const skipBtn = document.getElementById("skip-btn");
  const saveLetterBtn = document.getElementById("save-letter-btn");
  const trainMsg = document.getElementById("train-msg");
  const lettersGrid = document.getElementById("letters-grid");

  const textInput = document.getElementById("text-input");
  const generateTextBtn = document.getElementById("generate-text-btn");
  const photoInput = document.getElementById("photo-input");
  const recognizeBtn = document.getElementById("recognize-btn");
  const recognizedBox = document.getElementById("recognized-box");
  const recognizedText = document.getElementById("recognized-text");
  const generateRecognizedBtn = document.getElementById("generate-recognized-btn");
  const generateMsg = document.getElementById("generate-msg");
  const resultCard = document.getElementById("result-card");
  const resultImage = document.getElementById("result-image");
  const downloadPng = document.getElementById("download-png");
  const downloadPdf = document.getElementById("download-pdf");
  const paperOptions = document.getElementById("paper-options");
  const fontSizeOptions = document.getElementById("font-size-options");

  // ---------- State ----------
  let alphabet = [];
  let doneChars = new Set();
  let currentIndex = 0;
  let selectedPaper = "blank";
  let selectedFontSize = "standard";
  let papersLoaded = false;

  // ===================================================================
  // Переключение вкладок (универсально для любых .tabs с data-атрибутами)
  // ===================================================================
  function setupTabs(container, dataAttr, onSelect) {
    if (!container) return;
    container.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        container.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        onSelect(btn.dataset[dataAttr]);
      });
    });
  }

  setupTabs(document.querySelector("#auth-view .tabs"), "tab", (tab) => {
    loginForm.classList.toggle("hidden", tab !== "login");
    registerForm.classList.toggle("hidden", tab !== "register");
  });

  setupTabs(document.querySelector(".main-tabs"), "view", (view) => {
    trainView.classList.toggle("hidden", view !== "train");
    generateView.classList.toggle("hidden", view !== "generate");
  });

  setupTabs(document.querySelector("#generate-view .tabs"), "source", (source) => {
    document.getElementById("source-text").classList.toggle("hidden", source !== "text");
    document.getElementById("source-photo").classList.toggle("hidden", source !== "photo");
  });

  // ===================================================================
  // Авторизация
  // ===================================================================
  async function showApp(user) {
    authView.classList.add("hidden");
    appView.classList.remove("hidden");
    userBox.classList.remove("hidden");
    usernameLabel.textContent = user.username;
    await initTraining();
    await initPapers();
  }

  function showAuth() {
    appView.classList.add("hidden");
    authView.classList.remove("hidden");
    userBox.classList.add("hidden");
  }

  async function checkSession() {
    try {
      const user = await api.me();
      if (user) {
        await showApp(user);
      } else {
        showAuth();
      }
    } catch (e) {
      showAuth();
    }
  }

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    loginError.textContent = "";
    const fd = new FormData(loginForm);
    try {
      const user = await api.login(fd.get("username").trim(), fd.get("password"));
      await showApp(user);
    } catch (err) {
      loginError.textContent = err.message;
    }
  });

  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    registerError.textContent = "";
    const fd = new FormData(registerForm);
    try {
      const user = await api.register(fd.get("username").trim(), fd.get("password"));
      await showApp(user);
    } catch (err) {
      registerError.textContent = err.message;
    }
  });

  logoutBtn.addEventListener("click", async () => {
    try { await api.logout(); } catch (e) { /* игнорируем */ }
    showAuth();
  });

  // ===================================================================
  // Обучение почерку
  // ===================================================================
  const guideCtx = guideCanvas.getContext("2d");
  const drawCtx = drawCanvas.getContext("2d");
  drawCtx.lineWidth = 8;
  drawCtx.lineCap = "round";
  drawCtx.lineJoin = "round";
  drawCtx.strokeStyle = "#22283b";

  let drawing = false;
  let points = [];
  let hasStrokes = false;

  function canvasPoint(evt) {
    const rect = drawCanvas.getBoundingClientRect();
    const scaleX = drawCanvas.width / rect.width;
    const scaleY = drawCanvas.height / rect.height;
    return {
      x: (evt.clientX - rect.left) * scaleX,
      y: (evt.clientY - rect.top) * scaleY,
    };
  }

  drawCanvas.addEventListener("pointerdown", (evt) => {
    drawing = true;
    hasStrokes = true;
    const p = canvasPoint(evt);
    points = [p];
    drawCtx.beginPath();
    drawCtx.arc(p.x, p.y, drawCtx.lineWidth / 2, 0, Math.PI * 2);
    drawCtx.fillStyle = drawCtx.strokeStyle;
    drawCtx.fill();
    drawCanvas.setPointerCapture(evt.pointerId);
  });

  drawCanvas.addEventListener("pointermove", (evt) => {
    if (!drawing) return;
    const p = canvasPoint(evt);
    points.push(p);

    // Плавная аппроксимация квадратичными кривыми Безье через средние точки
    if (points.length >= 3) {
      const p0 = points[points.length - 3];
      const p1 = points[points.length - 2];
      const p2 = points[points.length - 1];

      const mid1 = { x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2 };
      const mid2 = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };

      drawCtx.beginPath();
      drawCtx.moveTo(mid1.x, mid1.y);
      drawCtx.quadraticCurveTo(p1.x, p1.y, mid2.x, mid2.y);
      drawCtx.stroke();
    } else if (points.length === 2) {
      drawCtx.beginPath();
      drawCtx.moveTo(points[0].x, points[0].y);
      drawCtx.lineTo(points[1].x, points[1].y);
      drawCtx.stroke();
    }
  });

  function stopDrawing(evt) {
    if (drawing && points.length > 2) {
      const p1 = points[points.length - 2];
      const p2 = points[points.length - 1];
      const mid = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
      drawCtx.beginPath();
      drawCtx.moveTo(mid.x, mid.y);
      drawCtx.lineTo(p2.x, p2.y);
      drawCtx.stroke();
    }
    drawing = false;
    points = [];
  }
  drawCanvas.addEventListener("pointerup", stopDrawing);
  drawCanvas.addEventListener("pointercancel", stopDrawing);
  drawCanvas.addEventListener("pointerleave", stopDrawing);

  function clearDrawCanvas() {
    drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    hasStrokes = false;
    points = [];
  }

  function drawGuide(char) {
    guideCtx.clearRect(0, 0, guideCanvas.width, guideCanvas.height);

    // Вспомогательные направляющие строчки как в прописях
    guideCtx.save();
    guideCtx.strokeStyle = "rgba(70, 110, 180, 0.20)";
    guideCtx.lineWidth = 1;
    guideCtx.setLineDash([4, 4]);

    // Верхняя линия для строчных букв
    guideCtx.beginPath();
    guideCtx.moveTo(12, 120);
    guideCtx.lineTo(guideCanvas.width - 12, 120);
    guideCtx.stroke();

    // Базовая линия строки
    guideCtx.strokeStyle = "rgba(70, 110, 180, 0.35)";
    guideCtx.beginPath();
    guideCtx.moveTo(12, 180);
    guideCtx.lineTo(guideCanvas.width - 12, 180);
    guideCtx.stroke();
    guideCtx.restore();

    guideCtx.fillStyle = "rgba(34, 40, 59, 0.16)";
    guideCtx.font = "180px 'Times New Roman', serif";
    guideCtx.textAlign = "center";
    guideCtx.textBaseline = "middle";
    guideCtx.fillText(char, guideCanvas.width / 2, guideCanvas.height / 2 + 6);
  }

  async function initTraining() {
    if (alphabet.length === 0) {
      const data = await api.getAlphabet();
      alphabet = data.alphabet;
    }
    await refreshProgress();
    renderLettersGrid();
    currentIndex = alphabet.findIndex((c) => !doneChars.has(c));
    if (currentIndex === -1) currentIndex = 0;
    loadLetter(currentIndex);
  }

  async function refreshProgress() {
    const data = await api.getProgress();
    doneChars = new Set(data.done);
    updateProgressBar();
  }

  function updateProgressBar() {
    const total = alphabet.length || 1;
    const done = doneChars.size;
    progressFill.style.width = `${Math.round((done / total) * 100)}%`;
    progressLabel.textContent = `${done} / ${total}`;
  }

  function renderLettersGrid() {
    lettersGrid.innerHTML = "";
    alphabet.forEach((char, idx) => {
      const chip = document.createElement("div");
      chip.className = "letter-chip";
      chip.textContent = char;
      chip.title = doneChars.has(char) ? "Уже записано - нажмите, чтобы переписать" : "Ещё не записано";
      if (doneChars.has(char)) chip.classList.add("done");
      chip.addEventListener("click", () => loadLetter(idx));
      lettersGrid.appendChild(chip);
    });
    highlightCurrentChip();
  }

  function highlightCurrentChip() {
    Array.from(lettersGrid.children).forEach((chip, idx) => {
      chip.classList.toggle("current", idx === currentIndex);
    });
  }

  function loadLetter(index) {
    currentIndex = index;
    const char = alphabet[currentIndex];
    drawGuide(char);
    clearDrawCanvas();
    trainMsg.textContent = "";
    highlightCurrentChip();
  }

  function advance() {
    let next = currentIndex + 1;
    if (next >= alphabet.length) next = 0;
    // ищем следующую незаписанную, иначе просто следующую по кругу
    const startedAt = next;
    while (doneChars.has(alphabet[next])) {
      next = (next + 1) % alphabet.length;
      if (next === startedAt) break;
    }
    loadLetter(next);
  }

  clearBtn.addEventListener("click", clearDrawCanvas);
  skipBtn.addEventListener("click", advance);

  saveLetterBtn.addEventListener("click", async () => {
    if (!hasStrokes) {
      trainMsg.textContent = "Сначала напишите букву на холсте.";
      return;
    }
    const char = alphabet[currentIndex];
    saveLetterBtn.disabled = true;
    trainMsg.textContent = "Сохраняем...";
    try {
      const dataUrl = drawCanvas.toDataURL("image/png");
      await api.saveSample(char, dataUrl);
      doneChars.add(char);
      updateProgressBar();
      renderLettersGrid();
      trainMsg.textContent = "Сохранено!";
      advance();
    } catch (err) {
      trainMsg.textContent = `Ошибка: ${err.message}`;
    } finally {
      saveLetterBtn.disabled = false;
    }
  });

  // ===================================================================
  // Выбор бумаги и размера текста
  // ===================================================================
  const FONT_SIZE_HINTS = {
    compact: "~38 строк на страницу (максимум текста)",
    standard: "~30 строк (как в школьной тетради)",
    large: "~22 строки на страницу",
  };

  async function initPapers() {
    if (papersLoaded) return;
    try {
      const data = await api.getPapers();
      selectedPaper = data.default || "blank";
      renderPaperOptions(data.papers);

      selectedFontSize = data.default_font_size || "standard";
      const fontSizes = data.font_sizes || [
        { key: "compact", label: "Мелкий" },
        { key: "standard", label: "Стандартный" },
        { key: "large", label: "Крупный" },
      ];
      renderFontSizeOptions(fontSizes);

      papersLoaded = true;
    } catch (err) {
      // если список не загрузился - остаёмся на значениях по умолчанию
      paperOptions.innerHTML = "";
    }
  }

  function renderPaperOptions(papers) {
    paperOptions.innerHTML = "";
    papers.forEach((p) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "paper-option" + (p.key === selectedPaper ? " selected" : "");
      btn.dataset.paper = p.key;

      const swatch = document.createElement("div");
      swatch.className = `paper-swatch ${p.key}`;

      const label = document.createElement("span");
      label.textContent = p.label;

      btn.appendChild(swatch);
      btn.appendChild(label);
      btn.addEventListener("click", () => {
        selectedPaper = p.key;
        paperOptions.querySelectorAll(".paper-option").forEach((el) => el.classList.remove("selected"));
        btn.classList.add("selected");
      });

      paperOptions.appendChild(btn);
    });
  }

  function renderFontSizeOptions(fontSizes) {
    if (!fontSizeOptions) return;
    fontSizeOptions.innerHTML = "";
    fontSizes.forEach((fs) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "font-size-btn" + (fs.key === selectedFontSize ? " selected" : "");
      btn.dataset.size = fs.key;

      const title = document.createElement("span");
      title.className = "font-size-label";
      title.textContent = fs.label;

      const hint = document.createElement("span");
      hint.className = "font-size-hint";
      hint.textContent = FONT_SIZE_HINTS[fs.key] || "";

      btn.appendChild(title);
      if (hint.textContent) btn.appendChild(hint);

      btn.addEventListener("click", () => {
        selectedFontSize = fs.key;
        fontSizeOptions.querySelectorAll(".font-size-btn").forEach((el) => el.classList.remove("selected"));
        btn.classList.add("selected");
      });

      fontSizeOptions.appendChild(btn);
    });
  }

  // ===================================================================
  // Генерация рукописного текста
  // ===================================================================
  function showResult(result) {
    resultCard.classList.remove("hidden");
    const bust = `?t=${Date.now()}`;
    resultImage.src = result.png_url + bust;
    downloadPng.href = result.png_url;
    downloadPdf.href = result.pdf_url;
    resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  generateTextBtn.addEventListener("click", async () => {
    const text = textInput.value.trim();
    generateMsg.textContent = "";
    if (!text) {
      generateMsg.textContent = "Введите текст.";
      return;
    }
    generateTextBtn.disabled = true;
    generateMsg.textContent = "Пишем вашим почерком...";
    try {
      const result = await api.generateFromText(text, selectedPaper, selectedFontSize);
      generateMsg.textContent = "";
      showResult(result);
    } catch (err) {
      generateMsg.textContent = `Ошибка: ${err.message}`;
    } finally {
      generateTextBtn.disabled = false;
    }
  });

  recognizeBtn.addEventListener("click", async () => {
    generateMsg.textContent = "";
    const file = photoInput.files[0];
    if (!file) {
      generateMsg.textContent = "Выберите файл фото.";
      return;
    }
    recognizeBtn.disabled = true;
    generateMsg.textContent = "Распознаём текст и пишем вашим почерком...";
    try {
      const result = await api.generateFromPhoto(file, selectedPaper, selectedFontSize);
      recognizedText.value = result.recognized_text || "";
      recognizedBox.classList.remove("hidden");
      generateMsg.textContent = "";
      showResult(result);
    } catch (err) {
      generateMsg.textContent = `Ошибка: ${err.message}`;
    } finally {
      recognizeBtn.disabled = false;
    }
  });

  generateRecognizedBtn.addEventListener("click", async () => {
    const text = recognizedText.value.trim();
    generateMsg.textContent = "";
    if (!text) {
      generateMsg.textContent = "Текст пуст.";
      return;
    }
    generateRecognizedBtn.disabled = true;
    generateMsg.textContent = "Пишем вашим почерком...";
    try {
      const result = await api.generateFromText(text, selectedPaper, selectedFontSize);
      generateMsg.textContent = "";
      showResult(result);
    } catch (err) {
      generateMsg.textContent = `Ошибка: ${err.message}`;
    } finally {
      generateRecognizedBtn.disabled = false;
    }
  });

  // ---------- Init ----------
  checkSession();
})();
