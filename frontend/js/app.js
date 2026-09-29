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
  const resetForm = document.getElementById("reset-form");
  const loginError = document.getElementById("login-error");
  const registerError = document.getElementById("register-error");
  const resetError = document.getElementById("reset-error");
  const forgotPasswordLink = document.getElementById("forgot-password-link");

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

  // Cursive state
  let selectedCursive = true;
  let selectedDensity = "standard";
  let currentCursiveText = "Съешь ещё этих мягких французских булок";
  let cursivePresetsData = null;
  let userLigatures = [];
  let isCursivePreview = true;
  let cursiveStrokes = []; // для отмены (undo)

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
    if (resetForm) resetForm.classList.toggle("hidden", tab !== "reset");
  });

  if (forgotPasswordLink) {
    forgotPasswordLink.addEventListener("click", (e) => {
      e.preventDefault();
      const resetTabBtn = document.querySelector('#auth-view .tabs .tab-btn[data-tab="reset"]');
      if (resetTabBtn) resetTabBtn.click();
    });
  }

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
    const adminBtn = document.getElementById('admin-btn');
    if (adminBtn) adminBtn.classList.toggle('hidden', !user.is_admin);
    await initTraining();
    await initCursiveTraining();
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

  if (resetForm) {
    resetForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (resetError) resetError.textContent = "";
      const fd = new FormData(resetForm);
      try {
        const user = await api.resetPassword(fd.get("username").trim(), fd.get("password"));
        await showApp(user);
      } catch (err) {
        if (resetError) resetError.textContent = err.message;
      }
    });
  }

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
    const W = guideCanvas.width;
    const H = guideCanvas.height;
    guideCtx.clearRect(0, 0, W, H);

    // Направляющие линии как в прописях
    const yTop    = Math.round(H * 0.18);  // верх заглавных букв
    const yMid    = Math.round(H * 0.42);  // верх строчных (x-height)
    const yBase   = Math.round(H * 0.68);  // базовая линия -- пишем по ней
    const yBottom = Math.round(H * 0.88);  // низ выносных (g, y, р, д)

    const xPad = 10;
    guideCtx.save();

    // Верхняя линия (заглавные) -- синяя пунктир
    guideCtx.strokeStyle = "rgba(100, 149, 237, 0.40)";
    guideCtx.lineWidth = 1;
    guideCtx.setLineDash([5, 5]);
    guideCtx.beginPath();
    guideCtx.moveTo(xPad, yTop);
    guideCtx.lineTo(W - xPad, yTop);
    guideCtx.stroke();

    // Верхняя линия строчных (x-height) -- синяя сплошная
    guideCtx.strokeStyle = "rgba(100, 149, 237, 0.55)";
    guideCtx.lineWidth = 1.2;
    guideCtx.setLineDash([]);
    guideCtx.beginPath();
    guideCtx.moveTo(xPad, yMid);
    guideCtx.lineTo(W - xPad, yMid);
    guideCtx.stroke();

    // Базовая линия -- красная, главная
    guideCtx.strokeStyle = "rgba(220, 53, 69, 0.75)";
    guideCtx.lineWidth = 2;
    guideCtx.setLineDash([]);
    guideCtx.beginPath();
    guideCtx.moveTo(xPad, yBase);
    guideCtx.lineTo(W - xPad, yBase);
    guideCtx.stroke();

    // Нижняя линия выносных -- синяя пунктир
    guideCtx.strokeStyle = "rgba(100, 149, 237, 0.35)";
    guideCtx.lineWidth = 1;
    guideCtx.setLineDash([3, 6]);
    guideCtx.beginPath();
    guideCtx.moveTo(xPad, yBottom);
    guideCtx.lineTo(W - xPad, yBottom);
    guideCtx.stroke();

    guideCtx.restore();

    // Буква-образец (прописная рукописная подсказка как в школьных прописях)
    guideCtx.save();
    guideCtx.fillStyle = "rgba(34, 40, 59, 0.16)";
    guideCtx.font = Math.round(H * 0.60) + "px 'Marck Script', 'Caveat', cursive";
    guideCtx.textAlign = "center";
    guideCtx.textBaseline = "alphabetic";
    guideCtx.fillText(char, W / 2, yBase);
    guideCtx.restore();
  }

  if (document.fonts) {
    document.fonts.load("120px 'Marck Script'").then(() => {
      if (alphabet && alphabet[currentIndex]) {
        drawGuide(alphabet[currentIndex]);
      }
    }).catch(() => {});
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

  // ===================================================================
  // Настройки слитности в генераторе (Generate View)
  // ===================================================================
  const cursiveToggleOn = document.getElementById("cursive-toggle-on");
  const cursiveToggleOff = document.getElementById("cursive-toggle-off");
  const cursiveDensityWrap = document.getElementById("cursive-density-wrap");
  const densityOptions = document.getElementById("density-options");

  if (cursiveToggleOn && cursiveToggleOff) {
    cursiveToggleOn.addEventListener("click", () => {
      selectedCursive = true;
      cursiveToggleOn.classList.add("selected");
      cursiveToggleOff.classList.remove("selected");
      if (cursiveDensityWrap) cursiveDensityWrap.classList.remove("hidden");
    });
    cursiveToggleOff.addEventListener("click", () => {
      selectedCursive = false;
      cursiveToggleOff.classList.add("selected");
      cursiveToggleOn.classList.remove("selected");
      if (cursiveDensityWrap) cursiveDensityWrap.classList.add("hidden");
    });
  }

  if (densityOptions) {
    densityOptions.querySelectorAll(".density-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        densityOptions.querySelectorAll(".density-btn").forEach((b) => b.classList.remove("selected"));
        btn.classList.add("selected");
        selectedDensity = btn.dataset.density;
      });
    });
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
      const result = await api.generateFromText(
        text,
        selectedPaper,
        selectedFontSize,
        selectedCursive,
        selectedDensity
      );
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
      const result = await api.generateFromPhoto(
        file,
        selectedPaper,
        selectedFontSize,
        selectedCursive,
        selectedDensity
      );
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
      const result = await api.generateFromText(
        text,
        selectedPaper,
        selectedFontSize,
        selectedCursive,
        selectedDensity
      );
      generateMsg.textContent = "";
      showResult(result);
    } catch (err) {
      generateMsg.textContent = `Ошибка: ${err.message}`;
    } finally {
      generateRecognizedBtn.disabled = false;
    }
  });

  // ===================================================================
  // Обучение слитности и связкам букв (Cursive Training)
  // ===================================================================
  const trainSubtabs = document.getElementById("train-subtabs");
  const trainLettersPanel = document.getElementById("train-letters-panel");
  const trainCursivePanel = document.getElementById("train-cursive-panel");

  const cursiveGuideCanvas = document.getElementById("cursive-guide-canvas");
  const cursiveDrawCanvas = document.getElementById("cursive-draw-canvas");
  const cursiveClearBtn = document.getElementById("cursive-clear-btn");
  const cursiveUndoBtn = document.getElementById("cursive-undo-btn");
  const cursiveSaveBtn = document.getElementById("cursive-save-btn");
  const cursiveTrainMsg = document.getElementById("cursive-train-msg");
  const currentCursiveTextEl = document.getElementById("current-cursive-text");
  const customCursiveInput = document.getElementById("custom-cursive-input");
  const customCursiveBtn = document.getElementById("custom-cursive-btn");
  const cursivePhrasesList = document.getElementById("cursive-phrases-list");
  const cursiveLigaturesList = document.getElementById("cursive-ligatures-list");
  const userLigaturesList = document.getElementById("user-ligatures-list");
  const cursiveTestInput = document.getElementById("cursive-test-input");
  const cursiveTestBtn = document.getElementById("cursive-test-btn");
  const cursiveTestPreviewBox = document.getElementById("cursive-test-preview-box");
  const cursiveTestImg = document.getElementById("cursive-test-img");
  const testPreviewCursive = document.getElementById("test-preview-cursive");
  const testPreviewSeparate = document.getElementById("test-preview-separate");

  let cursiveGuideCtx = null;
  let cursiveDrawCtx = null;
  let cursiveDrawing = false;
  let cursiveCurrentPoints = [];
  let cursiveHasStrokes = false;

  function initCursiveCanvas() {
    if (!cursiveDrawCanvas || !cursiveGuideCanvas) return;
    cursiveGuideCtx = cursiveGuideCanvas.getContext("2d");
    cursiveDrawCtx = cursiveDrawCanvas.getContext("2d");

    cursiveDrawCtx.lineWidth = 6;
    cursiveDrawCtx.lineCap = "round";
    cursiveDrawCtx.lineJoin = "round";
    cursiveDrawCtx.strokeStyle = "#22283b";

    function getCursivePoint(evt) {
      const rect = cursiveDrawCanvas.getBoundingClientRect();
      const scaleX = cursiveDrawCanvas.width / rect.width;
      const scaleY = cursiveDrawCanvas.height / rect.height;
      return {
        x: (evt.clientX - rect.left) * scaleX,
        y: (evt.clientY - rect.top) * scaleY,
      };
    }

    cursiveDrawCanvas.addEventListener("pointerdown", (evt) => {
      cursiveDrawing = true;
      cursiveHasStrokes = true;
      const p = getCursivePoint(evt);
      cursiveCurrentPoints = [p];

      cursiveDrawCtx.beginPath();
      cursiveDrawCtx.arc(p.x, p.y, cursiveDrawCtx.lineWidth / 2, 0, Math.PI * 2);
      cursiveDrawCtx.fillStyle = cursiveDrawCtx.strokeStyle;
      cursiveDrawCtx.fill();

      cursiveDrawCanvas.setPointerCapture(evt.pointerId);
    });

    cursiveDrawCanvas.addEventListener("pointermove", (evt) => {
      if (!cursiveDrawing) return;
      const p = getCursivePoint(evt);
      cursiveCurrentPoints.push(p);

      if (cursiveCurrentPoints.length >= 3) {
        const p0 = cursiveCurrentPoints[cursiveCurrentPoints.length - 3];
        const p1 = cursiveCurrentPoints[cursiveCurrentPoints.length - 2];
        const p2 = cursiveCurrentPoints[cursiveCurrentPoints.length - 1];

        const mid1 = { x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2 };
        const mid2 = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };

        cursiveDrawCtx.beginPath();
        cursiveDrawCtx.moveTo(mid1.x, mid1.y);
        cursiveDrawCtx.quadraticCurveTo(p1.x, p1.y, mid2.x, mid2.y);
        cursiveDrawCtx.stroke();
      } else if (cursiveCurrentPoints.length === 2) {
        cursiveDrawCtx.beginPath();
        cursiveDrawCtx.moveTo(cursiveCurrentPoints[0].x, cursiveCurrentPoints[0].y);
        cursiveDrawCtx.lineTo(cursiveCurrentPoints[1].x, cursiveCurrentPoints[1].y);
        cursiveDrawCtx.stroke();
      }
    });

    function stopCursiveDrawing() {
      if (cursiveDrawing && cursiveCurrentPoints.length > 0) {
        if (cursiveCurrentPoints.length > 2) {
          const p1 = cursiveCurrentPoints[cursiveCurrentPoints.length - 2];
          const p2 = cursiveCurrentPoints[cursiveCurrentPoints.length - 1];
          const mid = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
          cursiveDrawCtx.beginPath();
          cursiveDrawCtx.moveTo(mid.x, mid.y);
          cursiveDrawCtx.lineTo(p2.x, p2.y);
          cursiveDrawCtx.stroke();
        }
        // Сохраняем штрих в историю для отмены (undo)
        cursiveStrokes.push([...cursiveCurrentPoints]);
      }
      cursiveDrawing = false;
      cursiveCurrentPoints = [];
    }

    cursiveDrawCanvas.addEventListener("pointerup", stopCursiveDrawing);
    cursiveDrawCanvas.addEventListener("pointercancel", stopCursiveDrawing);
    cursiveDrawCanvas.addEventListener("pointerleave", stopCursiveDrawing);
  }

  function redrawCursiveStrokes() {
    if (!cursiveDrawCtx || !cursiveDrawCanvas) return;
    cursiveDrawCtx.clearRect(0, 0, cursiveDrawCanvas.width, cursiveDrawCanvas.height);
    cursiveHasStrokes = cursiveStrokes.length > 0;

    cursiveStrokes.forEach((stroke) => {
      if (stroke.length === 0) return;
      if (stroke.length === 1) {
        cursiveDrawCtx.beginPath();
        cursiveDrawCtx.arc(stroke[0].x, stroke[0].y, cursiveDrawCtx.lineWidth / 2, 0, Math.PI * 2);
        cursiveDrawCtx.fillStyle = cursiveDrawCtx.strokeStyle;
        cursiveDrawCtx.fill();
        return;
      }
      cursiveDrawCtx.beginPath();
      cursiveDrawCtx.moveTo(stroke[0].x, stroke[0].y);
      for (let i = 1; i < stroke.length - 1; i++) {
        const midX = (stroke[i].x + stroke[i + 1].x) / 2;
        const midY = (stroke[i].y + stroke[i + 1].y) / 2;
        cursiveDrawCtx.quadraticCurveTo(stroke[i].x, stroke[i].y, midX, midY);
      }
      cursiveDrawCtx.lineTo(stroke[stroke.length - 1].x, stroke[stroke.length - 1].y);
      cursiveDrawCtx.stroke();
    });
  }

  function clearCursiveCanvas() {
    if (!cursiveDrawCtx || !cursiveDrawCanvas) return;
    cursiveDrawCtx.clearRect(0, 0, cursiveDrawCanvas.width, cursiveDrawCanvas.height);
    cursiveStrokes = [];
    cursiveHasStrokes = false;
    cursiveCurrentPoints = [];
  }

  function drawCursiveGuide(text) {
    if (!cursiveGuideCtx || !cursiveGuideCanvas) return;
    const W = cursiveGuideCanvas.width;
    const H = cursiveGuideCanvas.height;
    cursiveGuideCtx.clearRect(0, 0, W, H);

    // Линовка как в каллиграфических прописях
    const yTop = Math.round(H * 0.22); // верх заглавных
    const yMid = Math.round(H * 0.46); // верх строчных (x-height)
    const yBase = Math.round(H * 0.70); // красная базовая линия
    const yBottom = Math.round(H * 0.90); // нижняя линия выносных

    const pad = 12;
    cursiveGuideCtx.save();

    // Наклонные линии письма (75 градусов, шаг 50px)
    cursiveGuideCtx.strokeStyle = "rgba(100, 149, 237, 0.16)";
    cursiveGuideCtx.lineWidth = 1;
    cursiveGuideCtx.setLineDash([3, 4]);
    const slantDx = Math.round((H * 0.8) / Math.tan((75 * Math.PI) / 180));
    for (let x = -slantDx; x < W + slantDx; x += 52) {
      cursiveGuideCtx.beginPath();
      cursiveGuideCtx.moveTo(x + slantDx, yTop - 10);
      cursiveGuideCtx.lineTo(x, yBottom + 10);
      cursiveGuideCtx.stroke();
    }

    // Верхняя заглавная линия (пунктир)
    cursiveGuideCtx.strokeStyle = "rgba(100, 149, 237, 0.40)";
    cursiveGuideCtx.setLineDash([5, 5]);
    cursiveGuideCtx.beginPath();
    cursiveGuideCtx.moveTo(pad, yTop);
    cursiveGuideCtx.lineTo(W - pad, yTop);
    cursiveGuideCtx.stroke();

    // Средняя линия строчных (сплошная)
    cursiveGuideCtx.strokeStyle = "rgba(100, 149, 237, 0.50)";
    cursiveGuideCtx.setLineDash([]);
    cursiveGuideCtx.beginPath();
    cursiveGuideCtx.moveTo(pad, yMid);
    cursiveGuideCtx.lineTo(W - pad, yMid);
    cursiveGuideCtx.stroke();

    // Красная базовая линия (главная)
    cursiveGuideCtx.strokeStyle = "rgba(220, 53, 69, 0.75)";
    cursiveGuideCtx.lineWidth = 2;
    cursiveGuideCtx.beginPath();
    cursiveGuideCtx.moveTo(pad, yBase);
    cursiveGuideCtx.lineTo(W - pad, yBase);
    cursiveGuideCtx.stroke();

    // Нижняя линия выносных (пунктир)
    cursiveGuideCtx.strokeStyle = "rgba(100, 149, 237, 0.35)";
    cursiveGuideCtx.lineWidth = 1;
    cursiveGuideCtx.setLineDash([3, 5]);
    cursiveGuideCtx.beginPath();
    cursiveGuideCtx.moveTo(pad, yBottom);
    cursiveGuideCtx.lineTo(W - pad, yBottom);
    cursiveGuideCtx.stroke();

    cursiveGuideCtx.restore();

    // Прописная подсказка текста (Marck Script)
    if (text) {
      cursiveGuideCtx.save();
      cursiveGuideCtx.fillStyle = "rgba(34, 40, 59, 0.16)";
      let fontSize = Math.round(H * 0.36);
      if (text.length <= 4) fontSize = Math.round(H * 0.48);
      else if (text.length > 25) fontSize = Math.round(H * 0.24);
      else if (text.length > 15) fontSize = Math.round(H * 0.30);

      cursiveGuideCtx.font = `${fontSize}px 'Marck Script', 'Caveat', cursive`;
      cursiveGuideCtx.textAlign = "left";
      cursiveGuideCtx.textBaseline = "alphabetic";

      // Если текст не помещается, мягко ужимаем шрифт
      const metrics = cursiveGuideCtx.measureText(text);
      if (metrics.width > W - 50) {
        fontSize = Math.floor(fontSize * ((W - 50) / metrics.width));
        cursiveGuideCtx.font = `${fontSize}px 'Marck Script', 'Caveat', cursive`;
      }

      cursiveGuideCtx.fillText(text, 24, yBase);
      cursiveGuideCtx.restore();
    }
  }

  function setCursiveTarget(text) {
    currentCursiveText = text.trim();
    if (currentCursiveTextEl) {
      currentCursiveTextEl.textContent = currentCursiveText;
    }
    drawCursiveGuide(currentCursiveText);
    clearCursiveCanvas();
    if (cursiveTrainMsg) cursiveTrainMsg.textContent = "";

    // Подсветка активного чипа
    document.querySelectorAll(".cursive-chip").forEach((chip) => {
      chip.classList.toggle("active", chip.dataset.text === currentCursiveText);
    });
  }

  async function loadCursivePresets() {
    try {
      const data = await api.getCursivePresets();
      cursivePresetsData = data;
      userLigatures = data.user_ligatures || [];

      // 1. Рендерим фразы
      if (cursivePhrasesList) {
        cursivePhrasesList.innerHTML = "";
        data.phrases.forEach((p, idx) => {
          const chip = document.createElement("button");
          chip.type = "button";
          chip.className = "cursive-chip" + (idx === 0 && !currentCursiveText ? " active" : "");
          chip.dataset.text = p.text;
          chip.textContent = p.title + ": «" + p.text.slice(0, 32) + "...»";
          chip.title = p.text;
          chip.addEventListener("click", () => setCursiveTarget(p.text));
          cursivePhrasesList.appendChild(chip);
        });
      }

      // 2. Рендерим популярные связки (лигатуры)
      if (cursiveLigaturesList) {
        cursiveLigaturesList.innerHTML = "";
        data.common_ligatures.forEach((lig) => {
          const chip = document.createElement("button");
          chip.type = "button";
          const hasUser = userLigatures.includes(lig);
          chip.className = "cursive-chip" + (hasUser ? " has-user-sample" : "");
          chip.dataset.text = lig;
          chip.textContent = lig;
          chip.title = hasUser ? "Связка уже записана! Нажмите для перезаписи" : "Нажмите, чтобы потренировать связку";
          chip.addEventListener("click", () => setCursiveTarget(lig));
          cursiveLigaturesList.appendChild(chip);
        });
      }

      // 3. Рендерим пользовательские сохраненные связки
      renderUserLigaturesList();
    } catch (e) {
      console.warn("Failed to load cursive presets:", e);
    }
  }

  function renderUserLigaturesList() {
    if (!userLigaturesList) return;
    userLigaturesList.innerHTML = "";
    if (!userLigatures || userLigatures.length === 0) {
      userLigaturesList.innerHTML =
        '<span class="hint-small">Пока нет дополнительных связок. Выберите связку выше или напишите своё слово.</span>';
      return;
    }

    userLigatures.forEach((lig) => {
      const tag = document.createElement("div");
      tag.className = "user-ligature-tag";

      const txt = document.createElement("span");
      txt.className = "tag-text";
      txt.textContent = lig;
      txt.style.cursor = "pointer";
      txt.title = "Нажмите, чтобы переписать";
      txt.addEventListener("click", () => setCursiveTarget(lig));

      const del = document.createElement("span");
      del.className = "tag-delete";
      del.textContent = "✕";
      del.title = "Удалить эту связку";
      del.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirm(`Удалить сохранённую связку «${lig}»?`)) return;
        try {
          await api.deleteSample(lig);
          userLigatures = userLigatures.filter((item) => item !== lig);
          renderUserLigaturesList();
          await loadCursivePresets();
        } catch (err) {
          alert("Ошибка удаления: " + err.message);
        }
      });

      tag.appendChild(txt);
      tag.appendChild(del);
      userLigaturesList.appendChild(tag);
    });
  }

  async function triggerCursiveTestPreview(text) {
    if (!cursiveTestPreviewBox || !cursiveTestImg) return;
    const testText = (text || (cursiveTestInput ? cursiveTestInput.value : "") || "Привет, как дела?").trim();
    if (!testText) return;

    cursiveTestPreviewBox.classList.remove("hidden");
    cursiveTestImg.style.opacity = "0.5";

    try {
      const res = await api.generatePreview(testText, isCursivePreview, selectedDensity);
      cursiveTestImg.src = res.data_url;
      cursiveTestImg.style.opacity = "1";
    } catch (err) {
      cursiveTestImg.style.opacity = "1";
    }
  }

  async function initCursiveTraining() {
    initCursiveCanvas();
    await loadCursivePresets();

    // Переключение между буквами и связками
    if (trainSubtabs) {
      setupTabs(trainSubtabs, "traintab", (tab) => {
        if (trainLettersPanel) trainLettersPanel.classList.toggle("hidden", tab !== "letters");
        if (trainCursivePanel) trainCursivePanel.classList.toggle("hidden", tab !== "cursive");
        if (tab === "cursive") {
          setCursiveTarget(currentCursiveText || "Съешь ещё этих мягких французских булок");
        }
      });
    }

    if (cursiveClearBtn) {
      cursiveClearBtn.addEventListener("click", clearCursiveCanvas);
    }

    if (cursiveUndoBtn) {
      cursiveUndoBtn.addEventListener("click", () => {
        if (cursiveStrokes.length > 0) {
          cursiveStrokes.pop();
          redrawCursiveStrokes();
        }
      });
    }

    if (customCursiveBtn && customCursiveInput) {
      const applyCustom = () => {
        const val = customCursiveInput.value.trim();
        if (val) {
          setCursiveTarget(val);
        }
      };
      customCursiveBtn.addEventListener("click", applyCustom);
      customCursiveInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          applyCustom();
        }
      });
    }

    if (cursiveSaveBtn) {
      cursiveSaveBtn.addEventListener("click", async () => {
        if (!cursiveHasStrokes) {
          cursiveTrainMsg.textContent = "Сначала напишите текст от руки на холсте.";
          return;
        }

        cursiveSaveBtn.disabled = true;
        cursiveTrainMsg.textContent = "Анализируем соединения и сохраняем связки...";

        try {
          const dataUrl = cursiveDrawCanvas.toDataURL("image/png");
          const res = await api.saveSample(currentCursiveText, dataUrl, true);

          if (!userLigatures.includes(currentCursiveText) && currentCursiveText.length > 1) {
            userLigatures.push(currentCursiveText);
            renderUserLigaturesList();
          }

          cursiveTrainMsg.textContent =
            "✨ Связки сохранены! Почерк обучен слитным переходам букв. Проверьте результат ниже:";
          await loadCursivePresets();
          await triggerCursiveTestPreview(currentCursiveText);
        } catch (err) {
          cursiveTrainMsg.textContent = `Ошибка: ${err.message}`;
        } finally {
          cursiveSaveBtn.disabled = false;
        }
      });
    }

    // Интерактивный тест слитности
    if (cursiveTestBtn) {
      cursiveTestBtn.addEventListener("click", () => {
        triggerCursiveTestPreview(cursiveTestInput ? cursiveTestInput.value : "");
      });
    }

    if (testPreviewCursive && testPreviewSeparate) {
      testPreviewCursive.addEventListener("click", () => {
        isCursivePreview = true;
        testPreviewCursive.classList.add("active");
        testPreviewSeparate.classList.remove("active");
        triggerCursiveTestPreview(cursiveTestInput ? cursiveTestInput.value : "");
      });

      testPreviewSeparate.addEventListener("click", () => {
        isCursivePreview = false;
        testPreviewSeparate.classList.add("active");
        testPreviewCursive.classList.remove("active");
        triggerCursiveTestPreview(cursiveTestInput ? cursiveTestInput.value : "");
      });
    }
  }

  // ---------- Init ----------
  checkSession();

  // ===================================================================
  // Admin Panel
  // ===================================================================
  const adminPanel  = document.getElementById('admin-panel');
  const adminClose  = document.getElementById('admin-close');
  const adminRefresh = document.getElementById('admin-refresh');
  const adminUsersBody = document.getElementById('admin-users-body');
  const adminMsg    = document.getElementById('admin-msg');
  const statUsers   = document.getElementById('stat-users');
  const statSamples = document.getElementById('stat-samples');
  const statAdmins  = document.getElementById('stat-admins');

  async function loadAdminStats() {
    try {
      const r = await fetch('/api/admin/stats', { credentials: 'include' });
      if (!r.ok) return;
      const d = await r.json();
      statUsers.textContent   = d.total_users;
      statSamples.textContent = d.total_samples;
      statAdmins.textContent  = d.admin_users;
    } catch (e) { /* ignore */ }
  }

  async function loadAdminUsers() {
    if (!adminMsg || !adminUsersBody) return;
    adminMsg.textContent = 'Загрузка...';
    adminUsersBody.innerHTML = '';
    try {
      const r = await fetch('/api/admin/users', { credentials: 'include' });
      if (!r.ok) { adminMsg.textContent = 'Ошибка загрузки'; return; }
      const d = await r.json();
      adminMsg.textContent = '';
      d.users.forEach(u => {
        const tr = document.createElement('tr');
        const date = u.created_at ? new Date(u.created_at).toLocaleDateString('ru-RU') : '—';
        const roleTag = u.is_admin
          ? '<span class="tag-admin">Админ</span>'
          : '<span class="tag-user">Пользователь</span>';
        tr.innerHTML =
          '<td>' + u.id + '</td>' +
          '<td class="username">' + u.username + '</td>' +
          '<td>' + u.sample_count + '</td>' +
          '<td>' + date + '</td>' +
          '<td>' + roleTag + '</td>' +
          '<td class="admin-actions">' +
            '<button class="btn-warning-sm" data-action="clear" data-uid="' + u.id + '">🗑 Буквы</button>' +
            (!u.is_admin ? '<button class="btn-danger-sm" data-action="delete" data-uid="' + u.id + '">✕ Удалить</button>' : '') +
          '</td>';
        adminUsersBody.appendChild(tr);
      });

      adminUsersBody.querySelectorAll('[data-action]').forEach(function(btn) {
        btn.addEventListener('click', async function() {
          const uid = btn.dataset.uid;
          const action = btn.dataset.action;
          if (action === 'delete') {
            if (!confirm('Удалить пользователя и все его данные?')) return;
            await fetch('/api/admin/users/' + uid, { method: 'DELETE', credentials: 'include' });
          } else if (action === 'clear') {
            if (!confirm('Очистить все образцы букв этого пользователя?')) return;
            await fetch('/api/admin/users/' + uid + '/samples', { method: 'DELETE', credentials: 'include' });
          }
          await loadAdminStats();
          await loadAdminUsers();
        });
      });
    } catch (e) {
      adminMsg.textContent = 'Ошибка: ' + e.message;
    }
  }

  async function openAdminPanel() {
    if (!adminPanel) return;
    adminPanel.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    await Promise.all([loadAdminStats(), loadAdminUsers()]);
  }

  function closeAdminPanel() {
    if (!adminPanel) return;
    adminPanel.classList.add('hidden');
    document.body.style.overflow = '';
  }

  const adminBtnEl = document.getElementById('admin-btn');
  if (adminBtnEl) adminBtnEl.addEventListener('click', openAdminPanel);
  if (adminClose) adminClose.addEventListener('click', closeAdminPanel);
  if (adminRefresh) adminRefresh.addEventListener('click', async function() {
    await loadAdminStats();
    await loadAdminUsers();
  });
  if (adminPanel) adminPanel.addEventListener('click', function(e) {
    if (e.target === adminPanel) closeAdminPanel();
  });

})();
