import { useEffect, useRef, useState } from "react";

import { useLang } from "../App.jsx";
import { t, PROFESSIONS } from "../i18n.js";
import { mockInterview } from "../api.js";
import Sources from "../Sources.jsx";

// Страница тренировки собеседования: выбор профессии + диалог с ботом-интервьюером.
export default function InterviewPage() {
  const { language } = useLang();

  const [profession, setProfession] = useState(PROFESSIONS[0]);
  const [started, setStarted] = useState(false);
  const [messages, setMessages] = useState([]); // { role, content, sources? }
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const endRef = useRef(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  // Запрос к боту: отправляем текущую историю и получаем очередную реплику интервьюера.
  const ask = async (history) => {
    setBusy(true);
    setError("");
    try {
      const apiMessages = history.map((m) => ({ role: m.role, content: m.content }));
      const data = await mockInterview({ profession, messages: apiMessages, language });
      setMessages([
        ...history,
        { role: "assistant", content: data.message, sources: data.sources },
      ]);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const start = () => {
    setStarted(true);
    setMessages([]);
    ask([]); // пустая история -> бот начинает интервью первым вопросом
  };

  const send = () => {
    const text = input.trim();
    if (!text || busy) return;
    const history = [...messages, { role: "user", content: text }];
    setMessages(history);
    setInput("");
    ask(history);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="chat">
      <p className="muted page-subtitle">{t(language, "interviewIntro")}</p>

      <div className="interview-setup">
        <label className="field">
          <span className="field__label">{t(language, "profession")}</span>
          <select
            value={profession}
            onChange={(e) => setProfession(e.target.value)}
            disabled={started && busy}
          >
            {PROFESSIONS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="btn btn-primary" onClick={start} disabled={busy}>
          {started ? t(language, "restart") : t(language, "startInterview")}
        </button>
      </div>

      {started && (
        <>
          <div className="chat__feed">
            {messages.map((m, i) => (
              <div key={i} className={`bubble bubble--${m.role}`}>
                <div className="bubble__role">
                  {m.role === "user" ? t(language, "you") : t(language, "assistant")}
                </div>
                <div className="bubble__text">{m.content}</div>
                {m.role === "assistant" && <Sources sources={m.sources} />}
              </div>
            ))}
            {busy && <p className="muted">{t(language, "typing")}</p>}
            {error && (
              <div className="error">
                {t(language, "errorPrefix")}: {error}
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="composer">
            <textarea
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={t(language, "answerPlaceholder")}
              disabled={busy}
            />
            <button
              type="button"
              className="btn btn-primary"
              onClick={send}
              disabled={busy || !input.trim()}
            >
              {t(language, "send")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
