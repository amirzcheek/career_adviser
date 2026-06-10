# Карьерный ИИ-консультант (Career Advisor) — KNUS

RAG-чат-бот для спортивного университета. Отвечает на карьерные вопросы студентов,
опираясь **только** на базу знаний вуза, приводит ссылки на источники и честно
сообщает, когда данных нет. Работает на локальных моделях внутри сети вуза —
никаких персональных данных наружу.

Фронтенд встраивается в портал **ai.knus.edu.kz** и выдержан в его стиле
(Vite + React + react-router-dom). Бэкенд — FastAPI с RAG-пайплайном поверх
Postgres + pgvector.

## Возможности
- **Чат-консультант** с потоковым ответом (SSE) и блоком источников под ответом.
- **Тренировка собеседования** (`/mock-interview`): бот задаёт вопросы по профессии,
  оценивает ответы и даёт обратную связь.
- **Три языка** интерфейса и ответов: казахский, русский, английский.
- Маршрутизация по языку: `kk` → KazLLM/Sherkala, `ru`/`en` → Qwen3 (OVMS).
- Эмбеддинги BGE-M3 (мультиязычные), векторный поиск в pgvector.

---

## Архитектура

```
career_adviser/
├── backend/                 # FastAPI + RAG
│   ├── app.py               # эндпоинты: /chat (SSE), /mock-interview, /admin/ingest, /health
│   ├── config.py            # вся конфигурация из переменных окружения
│   ├── embeddings.py        # клиент BGE-M3 (OpenAI-совместимый /embeddings)
│   ├── llm.py               # маршрутизация моделей по языку + стриминг + демо-режим
│   ├── store.py             # хранилище: PgVectorStore | JsonStore (локальный режим)
│   ├── rag.py               # извлечение контекста и системные промпты
│   ├── ingest.py            # пайплайн загрузки базы знаний
│   ├── migrations/001_init.sql   # таблица pgvector
│   ├── requirements.txt
│   └── .env.example
├── frontend/                # Vite + React (встраивается в портал)
│   └── src/ ...             # ChatPage, InterviewPage, i18n, auth-заглушка SSO
├── knowledge_base/          # стартовая база знаний (markdown с метаданными)
└── README.md
```

### Языковые модели и инфраструктура (через переменные окружения)
| Назначение | Переменные | Модель |
|---|---|---|
| Русский / английский | `LLM_BASE_URL`, `LLM_MODEL` | Qwen3-14B (OVMS) |
| Казахский | `KAZ_BASE_URL`, `KAZ_MODEL` | KazLLM-8B / Sherkala-8B |
| Эмбеддинги | `EMBED_BASE_URL`, `EMBED_MODEL` | BGE-M3 |
| Векторная БД | `DATABASE_URL` | Postgres + pgvector |

Все адреса берутся **только** из окружения — ничего не захардкожено.

> **Локальный режим без Postgres.** Если `DATABASE_URL` не задан, бэкенд хранит
> индекс в `backend/data/index.json`, а при отсутствии `EMBED_BASE_URL` использует
> лексический поиск. Если не заданы `LLM_BASE_URL`/`KAZ_BASE_URL`, включается
> демо-режим: ответ собирается из найденного контекста с пометкой, что модель не
> подключена. Это позволяет поднять и проверить весь пайплайн без внешних серверов.

---

## Быстрый старт (разработка)

### 1. Postgres + pgvector
Поднимите Postgres с расширением pgvector (например, в Docker):

```bash
docker run -d --name career-pg -p 5432:5432 \
  -e POSTGRES_USER=career -e POSTGRES_PASSWORD=career -e POSTGRES_DB=career_advisor \
  pgvector/pgvector:pg16
```

Примените миграцию (создаёт таблицу и индекс; размерность `vector(1024)` — под BGE-M3):

```bash
psql "postgresql://career:career@localhost:5432/career_advisor" \
  -f backend/migrations/001_init.sql
```

### 2. Бэкенд

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate    |  Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env       # (Linux/macOS: cp .env.example .env) и заполните адреса
```

Прогоните загрузку базы знаний (ingest) и запустите сервис:

```bash
python ingest.py             # читает knowledge_base/, считает эмбеддинги, пишет в индекс
uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

Проверка:
```bash
curl http://127.0.0.1:8080/health
curl -X POST http://127.0.0.1:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Чем занимается спортивный психолог?"}],"language":"ru"}'
```

### 3. Фронтенд

```bash
cd frontend
npm install
copy .env.example .env       # по умолчанию запросы идут на /api (прокси Vite -> :8080)
npm run dev                  # http://localhost:5173
```

В режиме разработки Vite проксирует `/api/*` на бэкенд (`http://127.0.0.1:8080`),
поэтому CORS локально не нужен.

---

## Эндпоинты API

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | состояние сервиса и индекса |
| POST | `/chat` | диалог, потоковая отдача (SSE) + источники |
| POST | `/mock-interview` | тренировка собеседования по профессии |
| POST | `/admin/ingest` | пересборка индекса (заголовок `X-Admin-Token`) |

**`POST /chat`** — тело: `{ "messages": [{role, content}], "language": "ru|kk|en" }`.
Ответ — поток SSE; каждое событие в поле `data` содержит JSON одного из типов:
`{"type":"sources",...}`, `{"type":"delta","text":"…"}`, `{"type":"done"}`.

**`POST /admin/ingest`** — пересборка после пополнения базы знаний:
```bash
curl -X POST http://127.0.0.1:8080/admin/ingest -H "X-Admin-Token: <ADMIN_TOKEN>"
```

---

## База знаний

Каталог `knowledge_base/` — markdown-файлы с метаданными во frontmatter:

```markdown
---
category: Карьерная траектория
language: ru
source: Профессия «Тренер»
---

# Тренер
...текст...
```

Поддерживаются `.md`, `.txt`, `.json`. Метаданные (`category`, `language`,
`source`) попадают в индекс и используются для показа источников.

Стартовое наполнение (на русском; помечены места для версий `kk`/`en`):
карьерные траектории (тренер, спортивный менеджер, реабилитолог/физиотерапевт,
учитель физкультуры, спортивный психолог, спортивный диетолог, фитнес-инструктор,
организатор соревнований, спортивный журналист) + гайды по резюме и собеседованию.

### Как пополнять базу знаний
1. Добавьте/измените файл в `knowledge_base/`.
2. Запустите переиндексацию: `python ingest.py` **или** `POST /admin/ingest`.

### Как добавлять актуальные вакансии (hh.kz / enbek.kz)
Сложите выгрузку в `knowledge_base/` как markdown с метаданными
`category: Вакансии`. Образец и рекомендуемый формат — в
[`knowledge_base/vacancies-example.md`](knowledge_base/vacancies-example.md).
Рекомендуемый формат одной вакансии:

```markdown
---
category: Вакансии
language: ru
source: hh.kz (вакансия № 0000000), 2026-06-01
---

**Должность:** …
**Организация:** …
**Обязанности:** …
**Требования:** …
**Контакты:** …
```

> Обязательно указывайте **источник и дату** — консультант ссылается на источник
> в ответе и не выдумывает вакансии.

JSON-формат (альтернатива): объект с полями `text`/`content`, `category`,
`language`, `source`.

После любой загрузки запускайте переиндексацию.

---

## Встраивание в портал ai.knus.edu.kz

1. **Сборка фронтенда:** `npm run build` → статика в `frontend/dist/`. Если
   приложение живёт в подкаталоге (`ai.knus.edu.kz/career/`), задайте `base: "/career/"`
   в `vite.config.js` перед сборкой.
2. **Прокси и скрытие бэкенда.** На проде reverse-proxy портала (nginx)
   проксирует `/api/*` на бэкенд карьерного консультанта. Так адрес бэкенда скрыт,
   а на прокси можно навесить авторизацию портала. Пример nginx:
   ```nginx
   location /career/api/ {
       proxy_pass http://career-backend:8080/;
       proxy_buffering off;            # важно для SSE-стриминга /chat
   }
   ```
   В этом случае на фронтенде оставьте `VITE_API_BASE=/career/api`.
3. **Авторизация / SSO.** В [`frontend/src/auth.js`](frontend/src/auth.js) —
   хук-заглушка `useAuth()` под вход портала / Azure AD SSO. Когда SSO подключат,
   возвращайте оттуда токен — он автоматически уйдёт в заголовке `Authorization`
   во все запросы к API. Также проверку токена можно повесить на reverse-proxy.
4. **CORS.** Если фронтенд и бэкенд на разных доменах (без общего прокси), укажите
   домен портала в `CORS_ORIGINS` бэкенда.

---

## Безопасность и приватность
- Все модели — локальные, в сети вуза. Персональные данные наружу не уходят.
- Пересборка индекса защищена токеном `ADMIN_TOKEN`.
- Адреса моделей, строка БД и токены — только в `.env` (не коммитятся).
