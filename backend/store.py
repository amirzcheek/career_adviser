# -*- coding: utf-8 -*-
"""
Хранилище фрагментов базы знаний и векторный поиск.

Две реализации за общим интерфейсом VectorStore:
  - PgVectorStore  — продакшн: Postgres + pgvector (включается, если задан DATABASE_URL);
  - JsonStore      — локальный режим: индекс в JSON-файле, поиск в памяти.
    Удобно для разработки и демо без поднятого Postgres.

Выбор реализации — функция get_store(): есть DATABASE_URL -> Postgres, иначе JSON.

Каждый фрагмент (чанк) — словарь:
  {
    "content":      текст фрагмента,
    "source":       имя файла-источника,
    "category":     категория из метаданных файла,
    "language":     язык фрагмента (ru/kk/en),
    "chunk_index":  порядковый номер фрагмента в документе,
    "embedding":    список float или None (None -> лексический поиск),
  }
"""

import os
import json
import math
import re
from typing import Optional

import config


def _vector_literal(vector: list[float]) -> str:
    """Преобразует вектор в строковый литерал pgvector: [0.1,0.2,...]."""
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


class VectorStore:
    """Базовый интерфейс хранилища."""

    def rebuild(self, chunks: list[dict]) -> int:
        """Полностью перезаписывает индекс переданными фрагментами.
        Возвращает число записанных фрагментов."""
        raise NotImplementedError

    def search(
        self, query_embedding: Optional[list[float]], query_text: str, k: int
    ) -> list[dict]:
        """Возвращает top-k наиболее релевантных фрагментов.
        Каждый результат — копия чанка с добавленным полем 'score' (0..1)."""
        raise NotImplementedError

    def count(self) -> int:
        """Число фрагментов в индексе."""
        raise NotImplementedError


# ─────────────────────────────── Postgres + pgvector ───────────────────────────────


class PgVectorStore(VectorStore):
    """Хранилище на Postgres с расширением pgvector.

    Использует psycopg2. Векторы передаются как строковые литералы с приведением
    ::vector — это избавляет от зависимости на numpy и пакет pgvector-python.
    """

    def __init__(self, dsn: str, table: str):
        self._dsn = dsn
        self._table = table

    def _connect(self):
        import psycopg2  # импорт здесь, чтобы локальный режим не требовал драйвер

        return psycopg2.connect(self._dsn)

    def rebuild(self, chunks: list[dict]) -> int:
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                # Полная пересборка: очищаем таблицу и заливаем заново.
                cur.execute(f"TRUNCATE TABLE {self._table} RESTART IDENTITY;")
                for ch in chunks:
                    embedding = ch.get("embedding")
                    if embedding is None:
                        raise RuntimeError(
                            "Для записи в pgvector нужны эмбеддинги, но сервер "
                            "эмбеддингов недоступен (EMBED_BASE_URL не задан)."
                        )
                    cur.execute(
                        f"""
                        INSERT INTO {self._table}
                            (content, source, category, language, chunk_index, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s::vector)
                        """,
                        (
                            ch["content"],
                            ch["source"],
                            ch.get("category"),
                            ch.get("language"),
                            ch.get("chunk_index", 0),
                            _vector_literal(embedding),
                        ),
                    )
            return len(chunks)
        finally:
            conn.close()

    def search(
        self, query_embedding: Optional[list[float]], query_text: str, k: int
    ) -> list[dict]:
        if query_embedding is None:
            raise RuntimeError(
                "Векторный поиск в pgvector требует эмбеддинг запроса, но сервер "
                "эмбеддингов недоступен (EMBED_BASE_URL не задан)."
            )
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                # Оператор <=> — косинусное расстояние; релевантность = 1 - расстояние.
                cur.execute(
                    f"""
                    SELECT content, source, category, language, chunk_index,
                           1 - (embedding <=> %s::vector) AS score
                    FROM {self._table}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (_vector_literal(query_embedding), _vector_literal(query_embedding), k),
                )
                rows = cur.fetchall()
            return [
                {
                    "content": r[0],
                    "source": r[1],
                    "category": r[2],
                    "language": r[3],
                    "chunk_index": r[4],
                    "score": float(r[5]),
                }
                for r in rows
            ]
        finally:
            conn.close()

    def count(self) -> int:
        conn = self._connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {self._table};")
                return int(cur.fetchone()[0])
        finally:
            conn.close()


# ─────────────────────────────── Локальный JSON-индекс ───────────────────────────────


def _tokenize(text: str) -> list[str]:
    """Простая токенизация для лексического поиска: слова из 2+ букв/цифр, в нижнем
    регистре. Поддерживает кириллицу, латиницу и казахские буквы."""
    return re.findall(r"[\wӘ-ӹ]{2,}", (text or "").lower(), flags=re.UNICODE)


def _cosine(a: list[float], b: list[float]) -> float:
    """Косинусная близость двух векторов (без numpy)."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class JsonStore(VectorStore):
    """Хранилище в JSON-файле с поиском в памяти.

    Если у фрагментов есть эмбеддинги — поиск косинусный. Если эмбеддингов нет
    (сервер BGE-M3 не настроен) — лексический поиск по пересечению слов. Так
    весь RAG-пайплайн остаётся работоспособным офлайн, для разработки и демо.
    """

    def __init__(self, path: str):
        self._path = path
        self._chunks: list[dict] = []
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._path):
            with open(self._path, encoding="utf-8") as f:
                self._chunks = json.load(f)

    def rebuild(self, chunks: list[dict]) -> int:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False)
        self._chunks = chunks
        return len(chunks)

    def search(
        self, query_embedding: Optional[list[float]], query_text: str, k: int
    ) -> list[dict]:
        if not self._chunks:
            return []

        scored: list[tuple[float, dict]] = []
        has_embeddings = query_embedding is not None and all(
            ch.get("embedding") for ch in self._chunks
        )

        if has_embeddings:
            # Семантический поиск по косинусной близости.
            for ch in self._chunks:
                scored.append((_cosine(query_embedding, ch["embedding"]), ch))
        else:
            # Лексический fallback: доля слов запроса, встретившихся во фрагменте.
            query_tokens = set(_tokenize(query_text))
            if not query_tokens:
                return []
            for ch in self._chunks:
                doc_tokens = set(_tokenize(ch["content"]))
                overlap = len(query_tokens & doc_tokens)
                score = overlap / len(query_tokens)
                scored.append((score, ch))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        results: list[dict] = []
        for score, ch in scored[:k]:
            if score <= 0:
                continue
            item = {key: ch.get(key) for key in
                    ("content", "source", "category", "language", "chunk_index")}
            item["score"] = float(score)
            results.append(item)
        return results

    def count(self) -> int:
        return len(self._chunks)


# ─────────────────────────────── Выбор реализации ───────────────────────────────


def get_store() -> VectorStore:
    """Возвращает хранилище: Postgres+pgvector при заданном DATABASE_URL,
    иначе локальный JSON-индекс."""
    if config.DATABASE_URL:
        return PgVectorStore(config.DATABASE_URL, config.DB_TABLE)
    return JsonStore(config.LOCAL_INDEX_PATH)


def backend_name() -> str:
    """Имя активного бэкенда хранилища — для /health и логов."""
    return "pgvector" if config.DATABASE_URL else "json-local"
