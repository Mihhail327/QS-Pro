import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel


# для асинхронности мы используем протокол postgresql+asyncpg
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://cyber_admin:baroque_pass@localhost:5432/qspro_vault"
).replace("postgresql://", "postgresql+asyncpg://")

# Создаем АСИНХРОННЫЙ движок промышленной базы данных PostgreSQL
# Пул соединений (pool_size, max_overflow) настроен под High-Load нагрузки
async_engine = create_async_engine(
    DATABASE_URL,
    echo=False, # Отключаем лишний спам логов в консоль на проде (для скорости)
    pool_size=20, # Сколько постоянных соединений держать в памяти под Flet-клиентов
    max_overflow=10, # Сколько дополнительных коннектов можно открыть при пиковой нагрузке
    future=True
)

# Фабрика асинхронных сессий
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False # Защита Pydantic-моделей от инвалидации данных после коммита
)


async def create_db_and_tables():
    """
    Автоматическая ковка структуры таблиц в PostgreSQL при старте шлюза.
    В асинхронной среде вызов метаданных требует выполнения в контексте движка."""
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    """
    Асинхронный генератор сессий для инжекции зависимостей (Depends) в роуты FastAPI.
    Гарантирует автоматическое закрытие коннекта после выполнения запроса.
    """
    async with async_session_factory() as session:
        yield session