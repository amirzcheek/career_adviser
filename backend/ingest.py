# -*- coding: utf-8 -*-
"""
Пайплайн загрузки базы знаний (ingest).

Шаги:
  1. Читает документы из knowledge_base/ (.md, .txt, .json).
  2. Разбирает метаданные (frontmatter в начале файла: category, language, source).
  3. Режет текст на чанки с перекрытием.
  4. Считает эмбеддинги через BGE-M3 (если сервер настроен).
  5. Полностью перезаписывает индекс в хранилище (pgvector или локальный JSON).

Запуск из командной строки:  python ingest.py
Также вызывается из эндпоинта POST /admin/ingest.
"""

import os
import json
import glob
from typing import Optional

import config
import embeddings
from store import get_store, backend_name


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Разбирает простой frontmatter в начале файла, ограниченный строками '---'.

    Поддерживаются строки вида `ключ: значение` (без вложенности — достаточно для
    category/language/source). Возвращает (метаданные, оставшийся текст).
    PyYAML не нужен — это убирает лишнюю зависимость.
    """
    meta: dict = {}
    stripped = text.lstrip("﻿")  # убираем BOM, если есть
    if stripped.startswith("---"):
        end = stripped.find("\n---", 3)
        if end != -1:
            header = stripped[3:end].strip()
            body = stripped[end + 4:].lstrip("\n")
            for line in header.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            return meta, body
    return meta, stripped


def _read_document(path: str) -> tuple[dict, str]:
    """Читает документ и возвращает (метаданные, текст).

    Для .json ожидается объект с полями text/content и (опционально) category,
    language, source. Для .md/.txt — frontmatter + текст.
    """
    with open(path, encoding="utf-8") as f:
        raw = f.read()

    filename = os.path.basename(path)
    if path.lower().endswith(".json"):
        data = json.loads(raw)
        meta = {
            "category": data.get("category"),
            "language": data.get("language"),
            "source": data.get("source", filename),
        }
        body = data.get("text") or data.get("content") or ""
        return meta, body

    meta, body = _parse_frontmatter(raw)
    meta.setdefault("source", filename)
    return meta, body


def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Режет текст на чанки длиной ~size символов с перекрытием overlap.

    Старается резать по границам абзацев/предложений: набираем абзацы, пока не
    превысим size; перекрытие сохраняет контекст на стыке соседних чанков.
    """
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        # Слишком длинный абзац режем жёстко по символам.
        if len(para) > size:
            if current:
                chunks.append(current.strip())
                current = ""
            for i in range(0, len(para), size - overlap):
                chunks.append(para[i:i + size].strip())
            continue

        if len(current) + len(para) + 2 <= size:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current.strip())
            # Начинаем новый чанк с «хвоста» предыдущего для перекрытия.
            tail = current[-overlap:] if overlap and current else ""
            current = f"{tail}\n\n{para}".strip() if tail else para

    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c]


def collect_chunks(knowledge_dir: Optional[str] = None) -> list[dict]:
    """Читает все документы базы знаний и возвращает список чанков с метаданными
    (без эмбеддингов)."""
    knowledge_dir = knowledge_dir or config.KNOWLEDGE_BASE_DIR
    patterns = ("*.md", "*.txt", "*.json")
    paths: list[str] = []
    for pat in patterns:
        paths.extend(glob.glob(os.path.join(knowledge_dir, "**", pat), recursive=True))
    paths.sort()

    chunks: list[dict] = []
    for path in paths:
        meta, body = _read_document(path)
        for idx, content in enumerate(
            _chunk_text(body, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        ):
            chunks.append({
                "content": content,
                "source": meta.get("source") or os.path.basename(path),
                "category": meta.get("category"),
                "language": (meta.get("language") or "ru"),
                "chunk_index": idx,
                "embedding": None,
            })
    return chunks


def run_ingest(knowledge_dir: Optional[str] = None) -> dict:
    """Полный цикл ingest: чтение -> чанкинг -> эмбеддинги -> запись в индекс.

    :return: сводка {documents_dir, chunks, embedded, store}.
    """
    chunks = collect_chunks(knowledge_dir)
    if not chunks:
        raise RuntimeError(
            f"В базе знаний нет документов: {knowledge_dir or config.KNOWLEDGE_BASE_DIR}"
        )

    # Считаем эмбеддинги пачкой. В офлайн-режиме (нет EMBED_BASE_URL) vectors=None —
    # чанки сохранятся без векторов, поиск будет лексическим (только для JSON-store).
    texts = [c["content"] for c in chunks]
    vectors = embeddings.embed_texts(texts)
    embedded = False
    if vectors is not None:
        for ch, vec in zip(chunks, vectors):
            ch["embedding"] = vec
        embedded = True

    store = get_store()
    written = store.rebuild(chunks)

    return {
        "documents_dir": knowledge_dir or config.KNOWLEDGE_BASE_DIR,
        "chunks": written,
        "embedded": embedded,
        "store": backend_name(),
    }


if __name__ == "__main__":
    summary = run_ingest()
    print("=== Ingest завершён ===")
    print(f"Каталог базы знаний : {summary['documents_dir']}")
    print(f"Хранилище           : {summary['store']}")
    print(f"Записано фрагментов  : {summary['chunks']}")
    print(f"С эмбеддингами       : {'да' if summary['embedded'] else 'нет (лексический поиск)'}")
