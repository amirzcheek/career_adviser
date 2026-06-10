# -*- coding: utf-8 -*-
"""
Клиент эмбеддингов (BGE-M3).

BGE-M3 — мультиязычная модель (kk/ru/en), отдаётся через OpenAI-совместимый
эндпоинт /embeddings. Адрес и имя модели берутся из переменных окружения.

Если эндпоинт эмбеддингов не настроен (EMBED_BASE_URL пуст), функции возвращают
None. Это сигнал вышестоящему коду перейти на лексический поиск — так весь
пайплайн остаётся работоспособным офлайн, для разработки и демо.
"""

from typing import Optional

import config


def is_configured() -> bool:
    """Настроен ли эндпоинт эмбеддингов."""
    return bool(config.EMBED_BASE_URL)


def embed_texts(texts: list[str]) -> Optional[list[list[float]]]:
    """Считает эмбеддинги для списка текстов.

    :return: список векторов той же длины, что и texts, либо None, если эндпоинт
        эмбеддингов не настроен.
    :raises RuntimeError: при ошибке обращения к серверу эмбеддингов.
    """
    if not is_configured():
        return None
    if not texts:
        return []

    # Импорт здесь, чтобы офлайн-режим не требовал библиотеку openai.
    from openai import OpenAI

    client = OpenAI(base_url=config.EMBED_BASE_URL, api_key=config.EMBED_API_KEY)
    try:
        response = client.embeddings.create(model=config.EMBED_MODEL, input=texts)
    except Exception as exc:  # noqa: BLE001 — оборачиваем любую ошибку сети/сервера.
        raise RuntimeError(f"Ошибка сервера эмбеддингов: {exc}") from exc

    # Сохраняем порядок: API возвращает элементы с полем index.
    ordered = sorted(response.data, key=lambda item: item.index)
    return [item.embedding for item in ordered]


def embed_query(text: str) -> Optional[list[float]]:
    """Считает эмбеддинг одного запроса (или None в офлайн-режиме)."""
    vectors = embed_texts([text])
    if vectors is None:
        return None
    return vectors[0] if vectors else None
