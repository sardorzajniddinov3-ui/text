// Небольшая обёртка над fetch для общения с бэкендом.
// Если фронтенд открыт с того же адреса, что и бэкенд (по умолчанию), достаточно
// относительных путей ("/api/..."). Если фронтенд запущен отдельно (другой порт/домен),
// поменяйте API_BASE на полный адрес бэкенда, например "http://localhost:5000".
const API_BASE = "";

async function apiRequest(path, { method = "GET", body, isFormData = false } = {}) {
  const options = {
    method,
    credentials: "same-origin",
    headers: {},
  };

  if (body !== undefined) {
    if (isFormData) {
      options.body = body; // FormData сам выставит правильный Content-Type
    } else {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
  }

  const resp = await fetch(API_BASE + path, options);
  let data = null;
  try {
    data = await resp.json();
  } catch (e) {
    data = null;
  }

  if (!resp.ok) {
    const message = (data && data.error) || `Ошибка запроса (${resp.status})`;
    throw new Error(message);
  }
  return data;
}

const api = {
  me: () => apiRequest("/api/auth/me"),
  login: (username, password) => apiRequest("/api/auth/login", { method: "POST", body: { username, password } }),
  register: (username, password) => apiRequest("/api/auth/register", { method: "POST", body: { username, password } }),
  resetPassword: (username, password) =>
    apiRequest("/api/auth/reset-password", { method: "POST", body: { username, password } }),
  logout: () => apiRequest("/api/auth/logout", { method: "POST" }),

  getAlphabet: () => apiRequest("/api/samples/alphabet"),
  getProgress: () => apiRequest("/api/samples/progress"),
  saveSample: (char, image, isCursive = false) =>
    apiRequest("/api/samples", { method: "POST", body: { char, image, is_cursive: isCursive } }),
  deleteSample: (char) => apiRequest(`/api/samples/${encodeURIComponent(char)}`, { method: "DELETE" }),

  getCursivePresets: () => apiRequest("/api/samples/cursive-presets"),
  getCursiveProfile: () => apiRequest("/api/samples/cursive-profile"),
  updateCursiveProfile: (profile) => apiRequest("/api/samples/cursive-profile", { method: "POST", body: profile }),
  generatePreview: (text, cursive = true, cursiveDensity = "standard", style = "my_handwriting") =>
    apiRequest("/api/generate/preview", { method: "POST", body: { text, cursive, cursive_density: cursiveDensity, style } }),

  getPapers: () => apiRequest("/api/generate/papers"),
  getStyles: () => apiRequest("/api/generate/styles"),
  generateFromText: (text, paper, fontSize, cursive = true, cursiveDensity = "standard", style = "my_handwriting") =>
    apiRequest("/api/generate/text", {
      method: "POST",
      body: { text, paper, font_size: fontSize, cursive, cursive_density: cursiveDensity, style },
    }),
  generateFromPhoto: (file, paper, fontSize, cursive = true, cursiveDensity = "standard", style = "my_handwriting") => {
    const form = new FormData();
    form.append("photo", file);
    form.append("paper", paper);
    if (fontSize) form.append("font_size", fontSize);
    form.append("cursive", cursive ? "true" : "false");
    form.append("cursive_density", cursiveDensity);
    form.append("style", style);
    return apiRequest("/api/generate/photo", { method: "POST", body: form, isFormData: true });
  },

  getMathPresets: () => apiRequest("/api/generate/math-presets"),
  getMathPreview: (formula) => apiRequest("/api/generate/math-preview", { method: "POST", body: { formula } }),
};
