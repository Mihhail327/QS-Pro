from datetime import datetime
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    """
    Модель пользователя экосистемы RellixCore.
    Хеширование паролей ложится на Argon2id через SecurityCore SDK.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=20, nullable=False)
    hashed_password: str # Хеш Argon2id от SecurityCore
    is_dev: bool = Field(default=False)
    encryption_salt: str # Уникальная соль пользователя для генерации ключей AES-GCM

    # Обратная связь: один юзер может владеть множеством сниппетов
    snippets: List["Snippet"] = Relationship(back_populates="user")


class Snippet(SQLModel, table=True):
    """
    Enterprise-модель Snippet.
    Поля content и note спроектированы под хранение зашифрованного AES-256-GCM base64-шума.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, nullable=False)
    
    # Открытые метаданные для полнотекстового Omni-Search и быстрой фильтрации
    title: str = Field(max_length=100, index=True, nullable=False)
    category: str = Field(index=True, nullable=False)  # "idea", "code", "study", "reminder", "important"
    sub_category: Optional[str] = Field(default="General", index=True)
    tags: Optional[str] = Field(default=None, index=True)  # Строка тегов для парсинга, пример: "#python #fastapi"
    language: Optional[str] = Field(default="text", index=True)  # Auto-Detect синтаксиса (для категории "code")
    image_url: Optional[str] = Field(default=None)  # Путь к дезинфицированному скриншоту (для категории "study")

    # ТЗ: Крипто-контейнеры (содержимое запечатано на клиенте/сервере)
    content: str  # Зашифрованный текст лекции или исходный код
    note: Optional[str] = Field(default=None)  # Зашифрованные Markdown-аннотации и чек-листы

    # ТЗ: Модуль "Напоминалка" (Сниппет-будильник)
    reminder_at: Optional[datetime] = Field(default=None, index=True)
    is_notified: bool = Field(default=False, index=True)
    
    # ТЗ: Nexus Links (Реляционный Граф Связей — Self-referencing Foreign Key)
    parent_snippet_id: Optional[int] = Field(default=None, foreign_key="snippet.id", index=True)
    
    # ТЗ: Local-First Синхронизация (Контроль версий для оффлайн-работы во Flet)
    version: int = Field(default=1, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Прямые связи сущностей базы данных
    user: User = Relationship(back_populates="snippets")