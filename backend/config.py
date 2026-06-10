# -*- coding: utf-8 -*-
"""
Конфигурация сервиса карьерного ИИ-консультанта.

Все адреса моделей, строка подключения к Postgres и токены берутся ТОЛЬКО из
переменных окружения (см. .env.example). Ничего не хардкодим — это требование
безопасности: сервис работает внутри сети вуза на локальных моделях.

Модуль ничего не вызывает на импорте, только читает окружение. Файл .env, если
он есть рядом, подхватывается через python-dotenv (необязательная зависимость).
"""

import os

# Необязательно подгружаем .env из текущего/родительского каталога, если
# установлен python-dotenv. На проде переменные обычно приходят из окружения
# контейнера, и dotenv просто ничего не делает.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # noqa: BLE001 — dotenv не обязателен.
    pass


def _split_csv(value: str) -> list[str]:
    """Разбирает список значений, разделённых запятыми, убирая пустые."""
    return [item.strip() for item in (value or "").split(",") if item.strip()]


# ── LLM для русского и английского (Qwen3-14B через OVMS, OpenAI-совместимый API) ──
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "not-needed")

# ── LLM для казахского (KazLLM-8B / Sherkala-8B, OpenAI-совместимый API) ──
KAZ_BASE_URL = os.getenv("KAZ_BASE_URL", "")
KAZ_MODEL = os.getenv("KAZ_MODEL", "")
KAZ_API_KEY = os.getenv("KAZ_API_KEY", "not-needed")

# ── Эмбеддинги (BGE-M3, мультиязычная kk/ru/en, OpenAI-совместимый /embeddings) ──
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "not-needed")
# Размерность вектора BGE-M3 — 1024. Должна совпадать с типом vector(...) в БД.
EMBED_DIM = int(os.getenv("EMBED_DIM", "1024"))

# ── Векторная БД (Postgres + pgvector) ──
# Если строка подключения не задана — сервис переходит в локальный режим
# (JSON-хранилище в backend/data/index.json), удобный для разработки и демо
# без поднятого Postgres.
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_TABLE = os.getenv("DB_TABLE", "kb_chunks")

# Путь к локальному JSON-индексу (fallback, когда нет DATABASE_URL).
LOCAL_INDEX_PATH = os.getenv(
    "LOCAL_INDEX_PATH",
    os.path.join(os.path.dirname(__file__), "data", "index.json"),
)

# ── База знаний и параметры RAG ──
KNOWLEDGE_BASE_DIR = os.getenv(
    "KNOWLEDGE_BASE_DIR",
    os.path.join(os.path.dirname(__file__), "..", "knowledge_base"),
)
# Размер чанка и перекрытие (в символах). Перекрытие сохраняет контекст на стыках.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
# Сколько фрагментов извлекать из базы под один запрос.
TOP_K = int(os.getenv("TOP_K", "5"))

# ── Безопасность и CORS ──
# Токен для защиты пересборки индекса (POST /admin/ingest).
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
# Домены, которым разрешён доступ к API из браузера. По умолчанию — портал вуза.
CORS_ORIGINS = _split_csv(os.getenv("CORS_ORIGINS", "https://ai.knus.edu.kz"))

# Человекочитаемые названия языков для системного промпта.
LANGUAGE_NAMES = {
    "ru": "русском",
    "kk": "казахском",
    "en": "английском (English)",
}


def language_name(language: str) -> str:
    """Возвращает название языка для подстановки в промпт; по умолчанию русский."""
    return LANGUAGE_NAMES.get((language or "ru").strip().lower(), LANGUAGE_NAMES["ru"])
