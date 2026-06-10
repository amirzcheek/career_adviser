// Хук авторизации — заглушка под существующий вход портала / Azure AD SSO.
//
// Сейчас возвращает пустого пользователя без токена. Когда на портале подключат
// SSO (Azure AD) или платформенный вход, замените тело useAuth: получайте токен
// из контекста портала (MSAL, cookie, postMessage от родительского окна и т.п.)
// и возвращайте его здесь. Токен автоматически добавится в заголовок Authorization
// всех запросов к API (см. api.js -> authHeaders()).

export function useAuth() {
  // TODO: интеграция с Azure AD SSO / входом портала ai.knus.edu.kz.
  // Пример будущей реализации:
  //   const token = await msalInstance.acquireTokenSilent(...);
  //   return { user: account, token };
  return {
    user: null, // { name, email } после подключения SSO
    token: null, // Bearer-токен после подключения SSO
    isAuthenticated: false,
  };
}

// Возвращает заголовки авторизации для fetch. Пока токена нет — пустой объект.
export function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Точка получения токена. Заглушка: читаем из localStorage, если портал его туда
// положит. После подключения SSO замените на реальный источник токена.
function getToken() {
  try {
    return localStorage.getItem("knus_access_token");
  } catch {
    return null;
  }
}
