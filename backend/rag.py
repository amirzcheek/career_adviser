# -*- coding: utf-8 -*-
"""
RAG-логика: извлечение контекста из базы знаний и сборка сообщений для модели.

Главный принцип сервиса: консультант отвечает ТОЛЬКО по найденным документам,
приводит источники и честно признаёт, когда данных нет. Здесь формируются
системные промпты, которые задают это поведение.
"""

from typing import Optional

import config
import embeddings
from store import get_store


def retrieve(query: str, k: Optional[int] = None) -> list[dict]:
    """Извлекает top-k релевантных фрагментов базы знаний под запрос.

    Эмбеддинг запроса считается через BGE-M3; если сервер эмбеддингов не настроен,
    хранилище переходит на лексический поиск (см. store.py).
    """
    k = k or config.TOP_K
    query_embedding = embeddings.embed_query(query)
    store = get_store()
    return store.search(query_embedding, query, k)


def format_sources(chunks: list[dict]) -> list[dict]:
    """Готовит компактный список источников для фронтенда (раскрывающийся блок
    под ответом). Несколько фрагментов из одного файла схлопываются в один
    источник, выдержки объединяются."""
    by_source: dict[str, dict] = {}
    for ch in chunks:
        src = ch.get("source") or "база знаний"
        entry = by_source.setdefault(
            src,
            {
                "source": src,
                "category": ch.get("category"),
                "language": ch.get("language"),
                "score": 0.0,
                "excerpts": [],
            },
        )
        entry["score"] = max(entry["score"], round(float(ch.get("score", 0.0)), 3))
        excerpt = (ch.get("content") or "").strip().replace("\n", " ")
        if len(excerpt) > 280:
            excerpt = excerpt[:280] + "…"
        entry["excerpts"].append(excerpt)
    # Сортируем по релевантности.
    return sorted(by_source.values(), key=lambda e: e["score"], reverse=True)


def _build_context_block(chunks: list[dict]) -> str:
    """Склеивает найденные фрагменты в блок КОНТЕКСТ с пометкой источника у каждого,
    чтобы модель могла сослаться на конкретный документ."""
    if not chunks:
        return "(в базе знаний не найдено релевантных материалов)"
    blocks = []
    for i, ch in enumerate(chunks, start=1):
        src = ch.get("source") or "база знаний"
        blocks.append(f"[Источник {i}: {src}]\n{ch.get('content', '').strip()}")
    return "\n\n".join(blocks)


# Базовые правила поведения консультанта — общие для чата и тренировки собеседования.
_BASE_RULES = (
    "Ты — карьерный консультант спортивного университета (KNUS). Помогаешь студентам "
    "и выпускникам выбирать профессию в сфере спорта, развивать карьеру, готовить "
    "резюме и проходить собеседования.\n\n"
    "Строгие правила:\n"
    "1. Отвечай ТОЛЬКО на основе блока КОНТЕКСТ ниже. Не выдумывай вакансии, "
    "зарплаты, факты и требования, которых нет в контексте.\n"
    "2. Если в контексте нет ответа — честно скажи об этом и предложи уточнить "
    "вопрос или обратиться в карьерный центр вуза. Не фантазируй.\n"
    "3. В конце ответа кратко укажи, на какие источники ты опирался "
    "(имена документов из контекста).\n"
    "4. Отвечай дружелюбно, конкретно и по делу, на {language_name} языке.\n"
)


def build_chat_messages(
    history: list[dict], language: str, chunks: list[dict]
) -> list[dict]:
    """Собирает сообщения для модели в режиме чата: системный промпт с правилами
    и контекстом + история диалога.

    :param history: список сообщений диалога [{role, content}, ...].
    """
    system = (
        _BASE_RULES.format(language_name=config.language_name(language))
        + "\n=== КОНТЕКСТ (фрагменты базы знаний) ===\n"
        + _build_context_block(chunks)
    )
    # История целиком; последний user-вопрос уже в ней.
    dialog = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    return [{"role": "system", "content": system}, *dialog]


def build_interview_messages(
    profession: str, history: list[dict], language: str, chunks: list[dict]
) -> list[dict]:
    """Собирает сообщения для режима тренировки собеседования.

    Бот играет роль интервьюера по выбранной профессии: задаёт по одному вопросу,
    оценивает ответ кандидата и даёт конструктивную обратную связь, опираясь на
    требования профессии из контекста.
    """
    system = (
        _BASE_RULES.format(language_name=config.language_name(language))
        + "\n\nРЕЖИМ ТРЕНИРОВКИ СОБЕСЕДОВАНИЯ.\n"
        + f"Профессия для интервью: «{profession}».\n"
        "Веди себя как доброжелательный интервьюер:\n"
        "- Если диалог только начинается — поприветствуй кандидата и задай первый "
        "вопрос по профессии.\n"
        "- На каждый ответ кандидата: сначала дай краткую обратную связь "
        "(что хорошо, что улучшить, опираясь на требования из контекста), затем "
        "задай следующий вопрос.\n"
        "- Задавай по одному вопросу за раз. Держись требований и навыков "
        "профессии из блока КОНТЕКСТ; не выдумывай несуществующих требований.\n"
        "\n=== КОНТЕКСТ (требования и материалы по профессии) ===\n"
        + _build_context_block(chunks)
    )
    dialog = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    # Если истории нет — подталкиваем модель начать интервью.
    if not dialog:
        dialog = [{"role": "user", "content": "Начнём собеседование."}]
    return [{"role": "system", "content": system}, *dialog]
