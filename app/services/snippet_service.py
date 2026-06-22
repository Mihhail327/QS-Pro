import logging
import json
from datetime import datetime
from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound

from app.models.snippet import Snippet, User
from app.auth.crypto import encrypt_data
from securitycore import input_sanitizer
from app.core.redis_cache import get_cached_snippets, set_snippets_cache, invalidate_user_cache

logger = logging.getLogger(__name__)

async def create_new_snippet(
    session: AsyncSession, user: User, category: str, content: str, sub_category: str,
    note: Optional[str], tags: Optional[str], parent_id: Optional[int], 
    reminder_at: Optional[str], image: Optional[str], clean_title: str
) -> Snippet:
    """Создание и запечатывание сниппета в БД"""
    assert user.id is not None  # Гарантируем линтеру, что ID существует
    
    # Берем готовую ссылку, которую передал роутер (сохраняем только для категории study)
    saved_image_url = image if category == "study" else None

    # Стерилизуем входящие данные перед шифрованием и запечатыванием в БД (до ORM)
    clean_content = str(input_sanitizer(content))
    clean_note = str(input_sanitizer(note)) if note else None

    enc_content = encrypt_data(clean_content, user.encryption_salt, category)
    enc_note = encrypt_data(clean_note, user.encryption_salt, category) if clean_note else None

    # АВТООПРЕДЕЛЕНИЕ ЯЗЫКА
    detected_lang = "text" # дефолт
    if category == "code":
        try:
            lexer = guess_lexer(content)
            detected_lang = lexer.name.lower()
        except ClassNotFound:
            detected_lang = "text"

    parsed_reminder = None
    if reminder_at:
        try:
            parsed_reminder = datetime.fromisoformat(reminder_at)
        except ValueError:
            pass

    formatted_tags = " ".join([f"#{t.strip('#')}" for t in tags.split() if t]) if tags else None

    new_item = Snippet(
        user_id=user.id, title=clean_title, content=enc_content, note=enc_note,
        category=category, 
        sub_category=sub_category, 
        language=detected_lang, # ДОБАВИЛИ ЭТО ПОЛЕ
        tags=formatted_tags,
        image_url=saved_image_url, 
        parent_snippet_id=parent_id, 
        reminder_at=parsed_reminder
    )

    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)
    
    # Инвалидируем кэш ТОЛЬКО для этого пользователя и категории
    await invalidate_user_cache(user.id)
    
    return new_item


async def get_user_snippets(session: AsyncSession, user_id: int, category: str = "all") -> List[Snippet]:
    # 1. Пытаемся получить из Redis
    try:
        cached_data = await get_cached_snippets(user_id, category)
        if cached_data:
            # Преобразуем словари из кэша обратно в полноценные объекты Snippet
            return [Snippet(**item) for item in cached_data]
    except Exception as e:
        logger.error(f"⚠️ Ошибка чтения кэша Redis: {e}")

    # 2. Postgres
    if category != "all":
        statement = select(Snippet).where(Snippet.user_id == user_id, Snippet.category == category)
    else:
        statement = select(Snippet).where(Snippet.user_id == user_id)
        
    result = await session.execute(statement)
    snippets = result.scalars().all()

    # 3. Сериализуем для кэша
    try:
        # model_dump_json() гарантирует сериализацию datetime объектов в ISO строки,
        # а json.loads превращает это обратно в чистый JSON-serializable dict для redis_cache
        snippets_data = [json.loads(s.model_dump_json()) for s in snippets]
        await set_snippets_cache(user_id, category, snippets_data)
    except Exception as e:
        logger.error(f"⚠️ Ошибка записи в кэш Redis: {e}")
        
    return list(snippets)