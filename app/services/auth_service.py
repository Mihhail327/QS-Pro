import secrets
from typing import Tuple, Optional
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snippet import User
from app.auth.security import hash_user_password, verify_user_password, validate_password_strength
from securitycore import input_sanitizer
from securitycore.analysis.password_analyzer import password_analyzer

async def register_user(username: str, password: str, is_dev: bool, session: AsyncSession) -> Tuple[bool, str]:
    """Регистрация юзера с проверкой энтропии SecurityCore."""
    if len(username) < 3 or len(username) > 20:
        return False, "Имя должно быть от 3 до 20 символов"

    if not validate_password_strength(password):
        analysis = password_analyzer(password)
        recommendation = "Пароль слишком слаб (низкая энтропия)."
        if analysis and isinstance(analysis, dict) and analysis.get("recommendations"):
            recommendation = analysis["recommendations"][0]
        return False, recommendation

    statement = select(User).where(User.username == username)
    result = await session.execute(statement)
    if result.scalars().first():
        return False, "Это секретное имя уже занято"

    salt = secrets.token_hex(16)
    new_user = User(
        username=username,
        hashed_password=hash_user_password(password),
        is_dev=is_dev,
        encryption_salt=salt
    )
    session.add(new_user)
    await session.commit()
    return True, "Регистрация успешна! Инициируйте вход."

async def authenticate_user(username: str, password: str, session: AsyncSession) -> Tuple[Optional[User], Optional[str]]:
    """Поиск юзера и проверка Argon2id хэша."""
    if not username or not password:
        return None, "Заполните все поля терминала"

    statement = select(User).where(User.username == username)
    result = await session.execute(statement)
    user = result.scalars().first()

    if not user or not verify_user_password(password, user.hashed_password):
        return None, "Неверный логин или крипто-ключ"

    if user.id is None:
        return None, "Критическая ошибка идентификатора"

    return user, None

async def get_user_status_data(user_id: int, session: AsyncSession) -> Optional[Tuple[str, str]]:
    """Извлечение безопасных данных профиля для хедера."""
    user = await session.get(User, user_id)
    if user and user.id is not None:
        is_dev_str = "dev" if user.is_dev else "user"
        safe_username = str(input_sanitizer(user.username))
        return safe_username, is_dev_str
    return None