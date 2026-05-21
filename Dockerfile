# Базовый образ Python (оставляем системную версию)
FROM python:3.13-slim

# =========================================================================
# МЕТАДАННЫЕ БРЕНДА RELLIXCORE 
# =========================================================================
LABEL org.opencontainers.image.title="RellixCore :: QuickSnippet Pro"
LABEL org.opencontainers.image.description="The Secure Cyber-Baroque Vault"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="NexO_ <mixa-amr@hotmail.com>"

# Установка системных утилит для компиляции
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Poetry глобально
RUN pip install --no-cache-dir poetry

# Рабочая директория внутри контейнера
WORKDIR /code

# Запрещаем Poetry создавать ненужные виртуальные окружения внутри Docker
RUN poetry config virtualenvs.create false

# Копируем чертежи зависимостей
COPY pyproject.toml poetry.lock* /code/

# Ставим библиотеки (включая asyncpg и psycopg2-binary для Postgres)
RUN poetry install --no-root --no-interaction --no-ansi

# Переносим весь код цитадели в контейнер
COPY . /code/

EXPOSE 8000

# Запуск командного мостика шлюза
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]