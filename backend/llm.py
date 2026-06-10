# -*- coding: utf-8 -*-
"""
Вызов языковых моделей по маршрутизации языка.

Маршрутизация:
  - kk        -> KazLLM-8B / Sherkala-8B (KAZ_*),
  - ru / en   -> Qwen3-14B через OVMS (LLM_*).

Все адреса и имена моделей — только из переменных окружения.

Если модель для нужного языка не настроена, включается демонстрационный режим:
ответ синтезируется из найденного контекста с пометкой, что LLM не подключён.
Это позволяет проверить весь пайплайн (/chat, /mock-interview) офлайн, без
доступа к серверам моделей.
"""

from typing import Iterator, Optional

import config


def pick_model(language: str) -> Optional[dict]:
    """Выбирает параметры подключения к модели по языку.

    :return: {base_url, model, api_key} или None, если модель для языка не
        настроена (тогда вызывающий код включает демо-режим).
    """
    language = (language or "ru").strip().lower()
    if language == "kk":
        base_url, model, api_key = config.KAZ_BASE_URL, config.KAZ_MODEL, config.KAZ_API_KEY
    else:
        base_url, model, api_key = config.LLM_BASE_URL, config.LLM_MODEL, config.LLM_API_KEY

    if not base_url or not model:
        return None
    return {"base_url": base_url, "model": model, "api_key": api_key}


def _client(model_cfg: dict):
    from openai import OpenAI

    return OpenAI(base_url=model_cfg["base_url"], api_key=model_cfg["api_key"])


def stream_chat(
    messages: list[dict],
    language: str,
    temperature: float = 0.4,
    max_tokens: int = 1024,
) -> Iterator[str]:
    """Потоковая генерация: отдаёт ответ модели по частям (дельтам текста).

    В демо-режиме (модель не настроена) отдаёт пояснительный текст, собранный из
    контекста, который уже подставлен в системное сообщение.
    """
    model_cfg = pick_model(language)
    if model_cfg is None:
        yield from _demo_stream(messages)
        return

    client = _client(model_cfg)
    try:
        stream = client.chat.completions.create(
            model=model_cfg["model"],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
    except Exception as exc:  # noqa: BLE001 — ошибка сети/модели.
        raise RuntimeError(f"Ошибка обращения к модели: {exc}") from exc


def complete_chat(
    messages: list[dict],
    language: str,
    temperature: float = 0.4,
    max_tokens: int = 1024,
) -> str:
    """Непотоковая генерация — возвращает весь ответ строкой.
    Используется в режиме тренировки собеседования."""
    model_cfg = pick_model(language)
    if model_cfg is None:
        return "".join(_demo_stream(messages))

    client = _client(model_cfg)
    try:
        response = client.chat.completions.create(
            model=model_cfg["model"],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Ошибка обращения к модели: {exc}") from exc
    return response.choices[0].message.content or ""


def is_demo(language: str) -> bool:
    """Работает ли сервис в демо-режиме для данного языка (модель не настроена)."""
    return pick_model(language) is None


def _demo_stream(messages: list[dict]) -> Iterator[str]:
    """Демо-ответ: коротко поясняет, что LLM не подключён, и приводит выдержку из
    найденного контекста. Системное сообщение содержит блок 'КОНТЕКСТ', откуда
    мы берём первые строки, чтобы ответ был осмысленным даже без модели."""
    system = next((m["content"] for m in messages if m.get("role") == "system"), "")
    user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
    )

    parts = [
        "⚠️ Демонстрационный режим: языковая модель не подключена "
        "(не заданы LLM_BASE_URL/KAZ_BASE_URL).\n\n",
        f"Ваш вопрос: «{user.strip()[:200]}».\n\n",
    ]

    # Вытаскиваем выдержку из блока КОНТЕКСТ системного промпта. Маркер с "==="
    # уникален (в тексте правил встречается слово «КОНТЕКСТ» без него).
    excerpt = ""
    marker = "=== КОНТЕКСТ"
    if marker in system:
        # Берём текст после заголовка блока (после строки "=== ... ===").
        after = system.split(marker, 1)[1]
        after = after.split("===", 1)[-1] if "===" in after else after
        excerpt = after.strip()[:600]
    if excerpt:
        parts.append(
            "На основе найденных в базе знаний фрагментов (ниже — выдержка):\n\n"
        )
        parts.append(excerpt)
        parts.append(
            "\n\nПодключите языковую модель, чтобы получить связный ответ "
            "с опорой на эти источники."
        )
    else:
        parts.append(
            "По вашему запросу в базе знаний не нашлось подходящих материалов."
        )

    # Отдаём по словам, имитируя потоковую генерацию для проверки фронтенда.
    for token in "".join(parts).split(" "):
        yield token + " "
