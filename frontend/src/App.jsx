import { createContext, useContext, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { LANGUAGES, t } from "./i18n.js";

// Контекст языка интерфейса/ответов — общий для всех страниц.
const LangContext = createContext({ language: "ru", setLanguage: () => {} });
export const useLang = () => useContext(LangContext);

// Общий каркас: шапка с языковым переключателем, навигацией и ссылкой на портал.
export default function App() {
  // Запоминаем выбранный язык между сессиями.
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
      <div className="app">
        <header className="app-header">
          <div className="app-header__inner">
            <span className="app-header__title">{t(language, "title")}</span>

            <nav className="app-nav">
              <NavLink to="/" end className="app-nav__link">
                {t(language, "navChat")}
              </NavLink>
              <NavLink to="/interview" className="app-nav__link">
                {t(language, "navInterview")}
              </NavLink>
            </nav>

            <div className="app-header__right">
              <select
                className="lang-select"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                aria-label="Язык / Тіл / Language"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </select>
              <a href="https://ai.knus.edu.kz/" className="app-header__portal">
                {t(language, "portal")}
              </a>
            </div>
          </div>
        </header>
        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </LangContext.Provider>
  );
}
