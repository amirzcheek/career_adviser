import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { useLang, useAuthCtx } from "../App.jsx";
import { t } from "../i18n.js";
import { getHealth, adminIngest } from "../api.js";

// Страница администрирования: состояние индекса + пересборка базы знаний.
// Доступна только админам (ссылка в навбаре тоже видна только им).
export default function AdminPage() {
  const { language } = useLang();
  const { isAdmin, loading } = useAuthCtx();

  const [health, setHealth] = useState(null);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState("");
  const [error, setError] = useState("");

  const refreshHealth = () => getHealth().then(setHealth).catch(() => setHealth(null));

  useEffect(() => {
    if (isAdmin) refreshHealth();
  }, [isAdmin]);

  // Пока грузится сессия — ничего не показываем; не-админа уводим на чат.
  if (loading) return <p className="muted">…</p>;
  if (!isAdmin) return <Navigate to="/" replace />;

  const rebuild = async () => {
    setError("");
    setResult("");
    setBusy(true);
    try {
      const data = await adminIngest(token);
      setResult(`${t(language, "rebuildOk")} ${data.chunks}`);
      await refreshHealth();
    } catch (e) {
      setError(`${t(language, "errorPrefix")} ${e.status ?? ""}: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <span className="badge">{t(language, "adminBadge")}</span>
      <h2 style={{ margin: "12px 0 4px", fontSize: 20 }}>{t(language, "adminTitle")}</h2>
      <p className="muted page-subtitle">{t(language, "adminDesc")}</p>

      <div className="admin-grid">
        {/* Состояние сервиса */}
        <div>
          <div className="admin-stat">
            <span>{t(language, "store")}</span>
            <span>{health?.store ?? "—"}</span>
          </div>
          <div className="admin-stat">
            <span>{t(language, "chunks")}</span>
            <span>{health?.chunks ?? "—"}</span>
          </div>
          <div className="admin-stat">
            <span>{t(language, "mode")}</span>
            <span>
              {health
                ? health.demo_mode
                  ? t(language, "modeDemo")
                  : t(language, "modeLive")
                : "—"}
            </span>
          </div>
        </div>

        {/* Пересборка индекса */}
        <label className="field">
          <span className="field__label">
            {t(language, "tokenLabel")}{" "}
            <span className="muted" style={{ fontWeight: 400 }}>
              · {t(language, "tokenHint")}
            </span>
          </span>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="ADMIN_TOKEN"
            autoComplete="off"
          />
        </label>

        <div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={rebuild}
            disabled={busy || !token.trim()}
          >
            {busy ? t(language, "rebuilding") : t(language, "rebuild")}
          </button>
        </div>

        {result && <div className="admin-result">{result}</div>}
        {error && <div className="error">{error}</div>}
      </div>
    </div>
  );
}
