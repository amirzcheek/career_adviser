// Клиент backend-API карьерного консультанта.
// Адрес берётся из VITE_API_BASE (см. .env.example). По умолчанию — относительный
// путь /api (прокси Vite в dev, reverse-proxy портала на проде).
import { authHeaders } from "./auth.js";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

// Потоковый чат (SSE). Отправляет историю и язык, по мере поступления данных
// вызывает колбэки:
//   onSources(list) — один раз, со списком источников;
//   onDelta(text)   — на каждый кусочек ответа;
//   onDone()        — по завершении.
// Возвращает функцию отмены запроса.
export function streamChat({ messages, language }, { onSources, onDelta, onError, onDone }) {
  const controller = new AbortController();

  (async () => {
    let res;
    try {
      res = await fetch(API_BASE + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ messages, language }),
        signal: controller.signal,
      });
    } catch (e) {
      if (e.name !== "AbortError") onError?.("Сеть недоступна или backend не запущен.");
      return;
    }

    if (!res.ok || !res.body) {
      const data = await res.json().catch(() => ({}));
      onError?.(data.detail || `HTTP ${res.status}`);
      return;
    }

    // Разбор потока SSE: события разделены пустой строкой, полезная нагрузка —
    // строки, начинающиеся с "data: " и содержащие JSON.
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sep;
        while ((sep = buffer.indexOf("\n\n")) !== -1) {
          const rawEvent = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          handleEvent(rawEvent, { onSources, onDelta, onError });
        }
      }
    } catch (e) {
      if (e.name !== "AbortError") onError?.(e.message);
      return;
    }
    onDone?.();
  })();

  return () => controller.abort();
}

function handleEvent(rawEvent, { onSources, onDelta, onError }) {
  for (const line of rawEvent.split("\n")) {
    if (!line.startsWith("data:")) continue;
    const json = line.slice(5).trim();
    if (!json) continue;
    let evt;
    try {
      evt = JSON.parse(json);
    } catch {
      continue;
    }
    if (evt.type === "sources") onSources?.(evt.sources || []);
    else if (evt.type === "delta") onDelta?.(evt.text || "");
    else if (evt.type === "error") onError?.(evt.message || "Ошибка генерации");
  }
}

// Режим тренировки собеседования (обычный JSON-ответ).
export async function mockInterview({ profession, messages, language }) {
  let res;
  try {
    res = await fetch(API_BASE + "/mock-interview", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ profession, messages, language }),
    });
  } catch (e) {
    throw new Error("Сеть недоступна или backend не запущен. " + e.message);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(typeof data.detail === "string" ? data.detail : `HTTP ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return data; // { message, sources, demo_mode }
}
