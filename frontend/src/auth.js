// Авторизация — интеграция с входом портала / Azure AD SSO (с заглушкой для dev).
//
// Топбар портала ai.knus.edu.kz берёт личность и роль из сессии:
//   GET /api/auth/session -> { user: { displayName, isAdmin, ... } }
// Здесь мы делаем то же самое: при встраивании в портал запрос вернёт реального
// пользователя; ссылка «Админка» в навбаре показывается только если isAdmin = true.
//
// Для локальной разработки (портал недоступен) включается заглушка. Чтобы
// проверить админ-режим локально, выполните в консоли браузера:
//   localStorage.setItem("knus_dev_admin", "1")  // и перезагрузите страницу.

import { useEffect, useState } from "react";

// Адрес сессии портала. Можно переопределить через VITE_SESSION_URL, если
// агент живёт в подкаталоге (например /career/) и сессия отдаётся с корня.
const SESSION_URL = import.meta.env.VITE_SESSION_URL ?? "/api/auth/session";

// Куда вести «Выход» и бренд — ссылки портала.
export const PORTAL_URL = import.meta.env.VITE_PORTAL_URL ?? "https://ai.knus.edu.kz/";
export const LOGOUT_URL =
  import.meta.env.VITE_LOGOUT_URL ?? "https://ai.knus.edu.kz/api/auth/logout";

// Хук авторизации: возвращает пользователя, флаг админа и состояние загрузки.
export function useAuth() {
  const [state, setState] = useState({
    user: null,
    isAdmin: false,
    isAuthenticated: false,
    loading: true,
  });

  useEffect(() => {
    let active = true;
    fetchSession().then((s) => active && setState({ ...s, loading: false }));
    return () => {
      active = false;
    };
  }, []);

  return state;
}

// Запрашивает сессию портала; при ошибке (локальная разработка) — заглушка.
async function fetchSession() {
  try {
    const res = await fetch(SESSION_URL, { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      const user = data.user || {};
      return {
        user,
        isAdmin: Boolean(user.isAdmin),
        isAuthenticated: true,
      };
    }
  } catch {
    /* портал недоступен — переходим на заглушку ниже */
  }
  return devFallback();
}

// Заглушка для локальной разработки без портала.
function devFallback() {
  let devAdmin = false;
  try {
    devAdmin = localStorage.getItem("knus_dev_admin") === "1";
  } catch {
    /* localStorage недоступен */
  }
  return {
    user: { displayName: "Гость (dev)", isAdmin: devAdmin },
    isAdmin: devAdmin,
    isAuthenticated: false,
  };
}

// Заголовки авторизации для запросов к API. Токен (после подключения SSO)
// кладётся порталом в localStorage; пока его нет — заголовков нет.
export function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function getToken() {
  try {
    return localStorage.getItem("knus_access_token");
  } catch {
    return null;
  }
}
