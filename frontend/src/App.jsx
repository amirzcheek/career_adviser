import { createContext, useContext, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { t } from "./i18n.js";
import { useAuth, PORTAL_URL, LOGOUT_URL } from "./auth.js";

// Контекст языка интерфейса/ответов — общий для всех страниц.
const LangContext = createContext({ language: "ru", setLanguage: () => {} });
export const useLang = () => useContext(LangContext);

// Контекст авторизации (личность + роль) — чтобы страницы знали об админ-правах.
const AuthContext = createContext({ user: null, isAdmin: false });
export const useAuthCtx = () => useContext(AuthContext);

// Порядок и подписи языкового переключателя — как на портале (RU / KZ / EN).
const LANG_PILL = [
  { value: "ru", label: "RU" },
  { value: "kk", label: "KZ" },
  { value: "en", label: "EN" },
];

// Общий каркас: топбар портала (бренд, языки, пользователь, админка, выход),
// заголовок агента с вкладками и область маршрута.
export default function App() {
  const auth = useAuth();

  const [language, setLanguageState] = useState(
    () => localStorage.getItem("knus_lang") || "ru"
  );
  const setLanguage = (lang) => {
    setLanguageState(lang);
    try {
      localStorage.setItem("knus_lang", lang);
    } catch {
      /* localStorage может быть недоступен */
    }
  };

  return (
    <LangContext.Provider value={{ language, setLanguage }}>
      <AuthContext.Provider value={auth}>
        <div className="page">
          {/* ── Топбар (стиль портала KNUS Digital) ── */}
          <header className="topbar">
            <div className="wrap topbar__inner">
              <div className="topbar-left">
                <a className="brand" href={PORTAL_URL}>
                  KNUS Digital
                </a>
                <div className="lang-switch" aria-label="Язык / Тіл / Language">
                  {LANG_PILL.map((l) => (
                    <button
                      key={l.value}
                      type="button"
                      className={`lang-btn${language === l.value ? " active" : ""}`}
                      onClick={() => setLanguage(l.value)}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="topbar-right">
                {!auth.loading && auth.user?.displayName && (
                  <span className="user-name">{auth.user.displayName}</span>
                )}
                {/* Ссылка «Админка» — только для админов */}
                {auth.isAdmin && (
                  <NavLink className="admin-link" to="/admin">
                    {t(language, "admin")}
                  </NavLink>
                )}
                <a className="logout-btn" href={LOGOUT_URL}>
                  {t(language, "logout")}
                </a>
              </div>
            </div>
          </header>

          {/* ── Заголовок агента + вкладки ── */}
          <div className="wrap">
            <section className="agent-hero">
              <h1>{t(language, "title")}</h1>
              <nav className="tabs">
                <NavLink to="/" end className="tab">
                  {t(language, "navChat")}
                </NavLink>
                <NavLink to="/interview" className="tab">
                  {t(language, "navInterview")}
                </NavLink>
              </nav>
            </section>

            <main className="app-main">
              <Outlet />
            </main>
          </div>
        </div>
      </AuthContext.Provider>
    </LangContext.Provider>
  );
}
