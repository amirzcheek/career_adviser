-- Миграция: таблица фрагментов базы знаний для векторного поиска (pgvector).
--
-- Применение:
--   psql "$DATABASE_URL" -f backend/migrations/001_init.sql
--
-- ВАЖНО: размерность vector(1024) соответствует модели BGE-M3. Если используется
-- другая модель эмбеддингов — приведите число к её размерности и к EMBED_DIM в .env.

-- Расширение pgvector (нужны права суперпользователя или предустановленное расширение).
CREATE EXTENSION IF NOT EXISTS vector;

-- Таблица чанков: текст фрагмента, метаданные и эмбеддинг.
CREATE TABLE IF NOT EXISTS kb_chunks (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT        NOT NULL,           -- текст фрагмента
    source      TEXT        NOT NULL,           -- имя файла-источника
    category    TEXT,                           -- категория (карьерная траектория, гайд и т.п.)
    language    TEXT,                           -- язык фрагмента: ru | kk | en
    chunk_index INTEGER     DEFAULT 0,          -- порядковый номер фрагмента в документе
    embedding   vector(1024),                   -- эмбеддинг BGE-M3
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Индекс для приближённого косинусного поиска (ANN). lists подбирается под объём
-- данных; для небольшой базы знаний 100 достаточно.
CREATE INDEX IF NOT EXISTS kb_chunks_embedding_idx
    ON kb_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Индекс по метаданным — на случай фильтрации по категории/языку.
CREATE INDEX IF NOT EXISTS kb_chunks_meta_idx
    ON kb_chunks (category, language);
