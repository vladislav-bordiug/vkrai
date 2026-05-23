# Local AI Assistant (deepagents-style)

Локальный ИИ-ассистент с отдельным React frontend (Vite + Nginx), FastAPI backend и PostgreSQL-хранилищем истории диалогов.

## Что реализовано

- Архитектура:
  - UI (web)
  - Backend-агент
  - Локальная БД с сущностями User/Session/Message
  - Адаптеры внешних API (Notion, OpenWeatherMap, Tavily, Todoist, Gmail, Google Calendar)
- Оркестрация LLM в стиле deepagents (планирование tool calls + выполнение + итоговый ответ)
- React frontend как отдельный сервис (контейнер) с историей сессий и продолжением чатов

## Стек

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy Async (PostgreSQL + asyncpg)
- OpenAI compatible API (модель задается через `AI_MODEL`, URL api через `AI_BASE_URL`, можно поставить любую модель из любого OpenAI-compatible API - deepseek, chatgpt, claude)
- deepagents (подключен зависимостью)

## Структура

- `app/main.py` — FastAPI API
- `app/agent.py` — агент-оркестратор
- `app/models.py` — SQLAlchemy модели `User`, `Session`, `Message`
- `app/repositories.py` — операции с БД
- `app/integrations/*.py` — async SDK/REST-обертки внешних API
- `frontend/*` — отдельное React приложение (Vite)
- `.env.example` — переменные окружения

## Модель БД

Реализована по диаграмме:

1. `User` (id, name, email)
2. `Session` (id, user_id, created_at, title)
3. `Message` (id, session_id, role[user|assistant], content, created_at)

Связи:

- User 1..N Session
- Session 1..N Message

## Подключенные API

1. Notion API — поиск и создание заметок/страниц
2. OpenWeatherMap — текущая погода
3. Tavily — веб-поиск
4. Todoist API — список/создание/редактирование задач
5. Gmail API — список и отправка сообщений
6. Google Calendar API — список/создание/редактирование событий

## Добавление новых тул

Тулы автоматически подтягиваются из папки app/integrations: 
каждая тула - это функция, которая начинается с "tool_", ее описание (завернутое в тройные кавычки """) также автоматически передается в системный промпт агента.

## Запуск

### Docker Compose

1. Создать `.env` на основе примера:

```bash
copy .env.example .env
```

2. Заполнить ключи API в `.env`.

3. Поднять проект:

```bash
docker compose up --build -d
```

4. Открыть сервисы:

- Frontend: `http://127.0.0.1:3000`
- Backend API: `http://127.0.0.1:8000`
- PostgreSQL: `127.0.0.1:5432`

5. Остановить проект:

```bash
docker compose down
```

## React UI возможности

- Список сессий пользователя по email
- Открытие истории выбранной сессии
- Продолжение существующего чата
- Создание нового чата
- Отображение tool trace

Дополнительный backend endpoint для React:

- `GET /api/users/sessions?email=...` — получить список сессий пользователя

## Google OAuth2 для Gmail и Calendar

Текущая реализация использует **refresh token flow**:

- backend берет `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` + `GOOGLE_REFRESH_TOKEN`
- обновляет access token через `https://oauth2.googleapis.com/token`
- применяет токен для Gmail/Calendar запросов

### .env

Все нужные переменные в [`.env.example`](.env.example):

1. `GOOGLE_CLIENT_ID`
2. `GOOGLE_CLIENT_SECRET`
3. `GOOGLE_REFRESH_TOKEN`
4. `GOOGLE_TOKEN_URL` (не менять)

### Как получить client_id/client_secret/refresh_token

1) Google Cloud Console
- Создать проект
- Включить Gmail API и Google Calendar API

2) OAuth Consent Screen
- Настроить consent screen (External/Internal)
- Добавить test users (если app в test mode)

3) OAuth Client
- Создать OAuth Client ID

4) Scope'ы
- Gmail: `https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.compose`
- Calendar: `https://www.googleapis.com/auth/calendar.readonly,https://www.googleapis.com/auth/calendar.events`

5) Получить refresh token
- Запросить код с `access_type=offline` и `prompt=consent`
- Обменять code на token response
- Сохранить `refresh_token` в `.env`

## Как агент понимает, какой тул вызывать

- У каждой тулы можно прописать описание.
- Системный промпт для планирования собирается из этих описаний.
- Это дает LLM контекст «когда и зачем вызывать каждый тул» и уменьшает случайные вызовы не того инструмента.

## Использование deepagents

- Агент создается напрямую через deepagents API.
- Модель инициализируется через LangChain.
- Тулы передаются в deepagents как список LangChain tools.
- Вызов генерации выполняется через deepagents invoke/ainvoke.

### Формат ответа deepagents

- Ответ deepagents может приходить строкой, dict-структурой или сообщением (Message-объект).
- Выполняется нормализация, чтобы стабильно извлекать финальный текст.

## Важно

- Бэкенд полностью асинхронный (FastAPI async endpoints + async DB + async HTTP tools).
- Полный проект поднимается через `docker-compose.yml` как 3 сервиса: `postgres`, `backend`, `frontend`.
- CORS backend настраивается через `CORS_ORIGINS`.
- Для Gmail/Google Calendar нужны валидные Google OAuth2 client credentials + refresh token.
- Для deepagents нужен валидный ключ провайдера модели (в текущем проекте используется `AI_API_KEY`, `AI_BASE_URL` и `AI_MODEL`).
- Текущий цикл: deepagents plan -> tool calls -> deepagents summary.

## PostgreSQL конфигурация

- В `docker-compose` используется сервис `postgres` с БД/пользователем `assistant`.
- Backend подключается по URL:
  `postgresql+asyncpg://assistant:assistant@postgres:5432/assistant`
- Для локального запуска вне Docker настройте `DATABASE_URL` в [`.env.example`](.env.example).

## Источники API

- deepagents: https://github.com/langchain-ai/deepagents
- Notion API: https://developers.notion.com/
- OpenWeatherMap API: https://openweathermap.org/api
- Tavily API: https://www.tavily.com/
- Todoist API Python: https://github.com/Doist/todoist-api-python
- Gmail API guides: https://developers.google.com/workspace/gmail/api/guides
- Google Calendar API guides: https://developers.google.com/workspace/calendar/api/guides/overview?hl=ru

