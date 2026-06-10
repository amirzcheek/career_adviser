import { useEffect, useRef, useState } from "react";

import { useLang } from "../App.jsx";
import { t } from "../i18n.js";
import { streamChat } from "../api.js";
import Sources from "../Sources.jsx";

// Страница чата с консультантом: лента сообщений, потоковый вывод, источники.
export default function ChatPage() {
  const { language } = useLang();

  // Каждое сообщение: { role: "user" | "assistant", content, sources? }
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState("");

  const cancelRef = useRef(null);
  const endRef = useRef(null);

  // Автопрокрутка к последнему сообщению.
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  // Отмена активного стрима при размонтировании.
  useEffect(() => () => cancelRef.current?.(), []);

  const send = () => {
    const text = input.trim();
    if (!text || streaming) return;
    setError("");

    const history = [...messages, { role: "user", content: text }];
    // Добавляем пустой ответ ассистента, который будем наполнять потоком.
    setMessages([...history, { role: "assistant", content: "", sources: [] }]);
    setInput("");
    setStreaming(true);

    // В API уходит только role+content (без служебных полей).
    const apiMessages = history.map((m) => ({ role: m.role, content: m.content }));

    cancelRef.current = streamChat(
      { messages: apiMessages, language },
      {
        onSources: (sources) =>
          setMessages((prev) => patchLast(prev, { sources })),
        onDelta: (delta) =>
          setMessages((prev) =>
            patchLast(prev, { content: prev[prev.length - 1].content + delta })
          ),
        onError: (msg) => {
          setError(msg);
          setStreaming(false);
        },
        onDone: () => setStreaming(false),
      }
    );
  };

  const onKeyDown = (e) => {
    // Enter — отправить, Shift+Enter — перенос строки.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="chat">
      <p className="muted page-subtitle">{t(language, "chatIntro")}</p>

      <div className="chat__feed">
        {messages.length === 0 && (
          <p className="chat__empty muted">{t(language, "emptyChat")}</p>
        )}

        {messages.map((m, i) => {
          const isLast = i === messages.length - 1;
          return (
            <div key={i} className={`bubble bubble--${m.role}`}>
              <div className="bubble__role">
                {m.role === "user" ? t(language, "you") : t(language, "assistant")}
              </div>
              <div className="bubble__text">
                {m.content}
                {m.role === "assistant" && isLast && streaming && (
                  <span className="typing-dot" aria-label={t(language, "typing")} />
                )}
              </div>
              {m.role === "assistant" && <Sources sources={m.sources} />}
            </div>
          );
        })}

        {error && <div className="error">{t(language, "errorPrefix")}: {error}</div>}
        <div ref={endRef} />
      </div>

      <div className="composer">
        <textarea
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={t(language, "placeholder")}
          disabled={streaming}
        />
        <button
          type="button"
          className="btn btn-primary"
          onClick={send}
          disabled={streaming || !input.trim()}
        >
          {streaming ? t(language, "typing") : t(language, "send")}
        </button>
      </div>
    </div>
  );
}

// Возвращает новый массив сообщений с обновлённым последним элементом.
function patchLast(messages, patch) {
  if (messages.length === 0) return messages;
  const copy = messages.slice();
  copy[copy.length - 1] = { ...copy[copy.length - 1], ...patch };
  return copy;
}
