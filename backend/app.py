# -*- coding: utf-8 -*-
"""
HTTP-сервис (FastAPI) карьерного ИИ-консультанта спортивного вуза.

RAG-чат-бот: отвечает на карьерные вопросы студентов по базе знаний университета
и приводит источники. Фронтенд (портал ai.knus.edu.kz) обращается к этим
эндпоинтам через серверный прокси.

Эндпоинты:
  - GET  /health         — проверка живости и состояния индекса.
  - POST /chat           — диалог с потоковой отдачей ответа (SSE) + источники.
  - POST /mock-interview — режим тренировки собеседования по профессии.
  - POST /admin/ingest   — пересборка индекса базы знаний (защищён токеном).
"""

import json
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import config
import llm
import rag
from ingest import run_ingest
from store import get_store, backend_name

app = FastAPI(
    title="Карьерный ИИ-консультант (KNUS)",
    description="RAG-консультант по карьере для спортивного университета. "
                "Отвечает по базе знаний вуза и приводит источники.",
    version="1.0.0",
)

# CORS: интерфейс на портале ai.knus.edu.kz обращается к API из браузера с
# другого домена. Список доменов — из переменной окружения CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ─────────────────────────────── Модели запросов ───────────────────────────────


class Message(BaseModel):
    """Одно сообщение диалога."""

    role: str = Field(..., description="user | assistant")
    content: str = Field(..., description="Текст сообщения")


class ChatRequest(BaseModel):
    """Запрос к чату: история диалога + язык ответа."""

    messages: list[Message] = Field(..., description="История диалога")
    language: str = Field("ru", description="Язык ответа: ru | kk | en")


class InterviewRequest(BaseModel):
    """Запрос к тренировке собеседования."""

    profession: str = Field(..., description="Профессия для собеседования")
    messages: list[Message] = Field(
        default_factory=list, description="История диалога (пусто — начать заново)"
    )
    language: str = Field("ru", description="Язык: ru | kk | en")


# ─────────────────────────────── Вспомогательное ───────────────────────────────


def _last_user_text(messages: list[Message]) -> str:
    """Возвращает текст последнего сообщения пользователя — это поисковый запрос."""
    for msg in reversed(messages):
        if msg.role == "user" and msg.content.strip():
            return msg.content.strip()
    return ""


def _sse(payload: dict) -> str:
    """Форматирует одно SSE-событие: одна строка data: с JSON-объектом."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ─────────────────────────────── Эндпоинты ───────────────────────────────


@app.get("/health")
def health():
    """Проверка живости сервиса и состояния индекса — для мониторинга портала."""
    try:
        chunks = get_store().count()
    except Exception as exc:  # noqa: BLE001 — БД может быть недоступна.
        return {"status": "degraded", "store": backend_name(), "error": str(exc)}
    return {
        "status": "ok",
        "store": backend_name(),
        "chunks": chunks,
        "demo_mode": llm.is_demo("ru"),
    }


@app.post("/chat")
def chat(req: ChatRequest):
    """Диалог с консультантом. Извлекает контекст из базы знаний и отдаёт ответ
    модели потоком (SSE). Сначала шлёт событие с источниками, затем дельты текста,
    затем событие done.

    Формат SSE-событий (поле data — JSON):
      {"type": "sources", "sources": [...]}
      {"type": "delta", "text": "..."}
      {"type": "done"}
      {"type": "error", "message": "..."}
    """
    if not req.messages:
        raise HTTPException(status_code=400, detail="Пустой список сообщений")

    query = _last_user_text(req.messages)
    if not query:
        raise HTTPException(status_code=400, detail="Нет вопроса пользователя")

    # Извлечение контекста выполняем до начала стрима, чтобы поймать ошибки БД здесь.
    try:
        chunks = rag.retrieve(query)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Ошибка поиска по базе: {exc}")

    history = [m.model_dump() for m in req.messages]
    messages = rag.build_chat_messages(history, req.language, chunks)
    sources = rag.format_sources(chunks)

    def event_stream():
        # 1) Источники — фронтенд покажет их в раскрывающемся блоке под ответом.
        yield _sse({"type": "sources", "sources": sources})
        # 2) Текст ответа по частям.
        try:
            for delta in llm.stream_chat(messages, req.language):
                yield _sse({"type": "delta", "text": delta})
        except Exception as exc:  # noqa: BLE001 — ошибка модели уже в процессе стрима.
            yield _sse({"type": "error", "message": str(exc)})
            return
        yield _sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/mock-interview")
def mock_interview(req: InterviewRequest):
    """Режим тренировки собеседования: бот задаёт вопросы по профессии, оценивает
    ответы и даёт обратную связь. Возвращает JSON с очередной репликой интервьюера
    и источниками (требования профессии из базы знаний)."""
    if not req.profession.strip():
        raise HTTPException(status_code=400, detail="Не указана профессия")

    # Контекст ищем по профессии + последнему ответу кандидата.
    query = (req.profession + " " + _last_user_text(req.messages)).strip()
    try:
        chunks = rag.retrieve(query)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Ошибка поиска по базе: {exc}")

    history = [m.model_dump() for m in req.messages]
    messages = rag.build_interview_messages(
        req.profession, history, req.language, chunks
    )

    try:
        answer = llm.complete_chat(messages, req.language)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "message": answer,
        "sources": rag.format_sources(chunks),
        "demo_mode": llm.is_demo(req.language),
    }


@app.post("/admin/ingest")
def admin_ingest(x_admin_token: Optional[str] = Header(default=None)):
    """Пересборка индекса базы знаний. Защищён токеном из переменной окружения
    ADMIN_TOKEN — передаётся в заголовке X-Admin-Token."""
    if not config.ADMIN_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_TOKEN не задан на сервере — пересборка отключена.",
        )
    if x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Неверный admin-токен")

    try:
        summary = run_ingest()
    except Exception as exc:  # noqa: BLE001 — ошибки чтения/эмбеддингов/записи.
        raise HTTPException(status_code=500, detail=f"Ошибка ingest: {exc}")
    return {"status": "ok", **summary}
