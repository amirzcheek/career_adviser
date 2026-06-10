import { useState } from "react";

import { useLang } from "./App.jsx";
import { t } from "./i18n.js";

// Раскрывающийся блок источников под ответом ассистента.
export default function Sources({ sources }) {
  const { language } = useLang();
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources">
      <button
        type="button"
        className="sources__toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {open ? "▾" : "▸"} {t(language, "sources")} ({sources.length})
      </button>
      {open && (
        <ul className="sources__list">
          {sources.map((s, i) => (
            <li key={i} className="sources__item">
              <span className="sources__name">{s.source}</span>
              {s.category && <span className="sources__cat"> · {s.category}</span>}
              {s.excerpts?.[0] && (
                <p className="sources__excerpt">{s.excerpts[0]}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
