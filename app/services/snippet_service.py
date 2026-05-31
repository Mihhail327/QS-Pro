import logging
from datetime import datetime
from typing import Optional, List
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snippet import Snippet, User
from app.auth.crypto import encrypt_data

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

    enc_content = encrypt_data(content, user.encryption_salt, category)
    enc_note = encrypt_data(note, user.encryption_salt, category) if note else None

    parsed_reminder = None
    if reminder_at:
        try:
            parsed_reminder = datetime.fromisoformat(reminder_at)
        except ValueError:
            pass

    formatted_tags = " ".join([f"#{t.strip('#')}" for t in tags.split() if t]) if tags else None

    new_item = Snippet(
        user_id=user.id, title=clean_title, content=enc_content, note=enc_note,
        category=category, sub_category=sub_category, tags=formatted_tags,
        image_url=saved_image_url, parent_snippet_id=parent_id, reminder_at=parsed_reminder
    )
    
    session.add(new_item)
    await session.commit()
    return new_item


async def get_user_snippets(session: AsyncSession, user_id: int, category: str = "all") -> List[Snippet]:
    """Извлечение сниппетов из базы с сортировкой по времени"""
    statement = select(Snippet).where(Snippet.user_id == user_id).order_by(desc(Snippet.created_at))
    result = await session.execute(statement)
    snippets = result.scalars().all()
    
    if category != "all":
        return [s for s in snippets if s.category == category]
    return list(snippets)