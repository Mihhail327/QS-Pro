import io
import json
import logging
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlmodel import select, desc  # Изменили импорт, добавили desc!
from sqlalchemy.ext.asyncio import AsyncSession

# Интеграция инфраструктуры RellixCore
from app.database.config import get_session
from app.models.snippet import Snippet, User
from app.auth.security import get_current_user_from_cookie
from app.auth.crypto import encrypt_data, decrypt_data

# Твой боевой SDK SecurityCore
from securitycore import input_sanitizer

# Pillow для дезинфекции скриншотов категории "Учеба"
from PIL import Image

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/snippets", tags=["snippets"])

UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/create", response_class=HTMLResponse)
async def create_snippet(
    request: Request,
    category: str = Form(...),
    content: str = Form(...),
    sub_category: str = Form("General"),
    note: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    parent_snippet_id: Optional[int] = Form(None),
    reminder_at: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session)
):
    user_id = get_current_user_from_cookie(request)
    if not user_id:
        return HTMLResponse(content="<span class='text-red-400'>❌ Сессия истекла. Войдите снова.</span>", status_code=401)

    user = await session.get(User, user_id)
    if not user or user.id is None:  # Гарантируем линтеру, что user.id существует
        return HTMLResponse(content="<span class='text-red-400'>❌ Пользователь не найден.</span>", status_code=404)

    # 1. Очистка скриншотов через Pillow
    saved_image_url = None
    if category == "study" and image and image.filename:
        try:
            image_bytes = await image.read()
            img = Image.open(io.BytesIO(image_bytes))
            clean_filename = f"clean_{user.id}_{int(datetime.utcnow().timestamp())}.jpg"
            file_path = os.path.join(UPLOAD_DIR, clean_filename)
            img.convert("RGB").save(file_path, "JPEG", quality=85)
            saved_image_url = f"/static/uploads/{clean_filename}"
        except Exception as e:
            logger.error(f"⚠️ Сбой дезинфекции Pillow: {e}")
            return HTMLResponse(content="<span class='text-red-400'>❌ Ошибка обработки скриншота.</span>")

    # 2. Крипто-запечатывание AES-256-GCM
    encrypted_content = encrypt_data(content, user.encryption_salt, category)
    encrypted_note = encrypt_data(note, user.encryption_salt, category) if note else None

    if tags:
        tags = " ".join([f"#{t.strip('#')}" for t in tags.split() if t])

    parsed_reminder = None
    if reminder_at:
        try:
            parsed_reminder = datetime.fromisoformat(reminder_at)
        except ValueError:
            pass

    # Фикс багов типизации: принудительно приводим результат санитайзера к str
    clean_title = str(input_sanitizer(content[:30] + "..."))

    # 3. Ковка сущности
    new_item = Snippet(
        user_id=int(user.id),  # Жесткое приведение к int для Pylance
        title=clean_title,
        content=encrypted_content,
        note=encrypted_note,
        category=category,
        sub_category=sub_category,
        tags=tags,
        image_url=saved_image_url,
        parent_snippet_id=parent_snippet_id,
        reminder_at=parsed_reminder
    )
    
    session.add(new_item)
    await session.commit()

    return await list_snippets(request, None, "all", session)


@router.get("/list", response_class=HTMLResponse)
async def list_snippets(
    request: Request, 
    q: Optional[str] = None, 
    category: str = "all", 
    session: AsyncSession = Depends(get_session)
):
    user_id = get_current_user_from_cookie(request)
    if not user_id: 
        return HTMLResponse(content="<p class='text-gray-500'>Пожалуйста, авторизуйтесь.</p>")

    user = await session.get(User, user_id)
    if not user or user.id is None:
        return HTMLResponse(content="<p class='text-gray-500'>Юзер не найден.</p>")

    # Фикс бага №4: Правильное использование desc() в SQLModel / SQLAlchemy
    statement = select(Snippet).where(Snippet.user_id == user.id).order_by(desc(Snippet.created_at))
    query_result = await session.execute(statement)
    results = query_result.scalars().all()

    html = ""
    for s in results:
        if category != "all" and s.category != category:
            continue

        decrypted_text = decrypt_data(s.content, user.encryption_salt, s.category) or "[Ошибка декодирования]"
        decrypted_note = decrypt_data(s.note, user.encryption_salt, s.category) if s.note else ""

        # Принудительный каст результатов санитайзера к строкам (Защита от багов оператора +)
        safe_text = str(input_sanitizer(decrypted_text))
        safe_note = str(input_sanitizer(decrypted_note)) if decrypted_note else ""

        if q:
            query = q.lower()
            if query.startswith("#"):
                if not s.tags or query not in s.tags.lower(): 
                    continue
            elif query.startswith("lang:"):
                target_lang = query.replace("lang:", "").strip()
                if not s.language or target_lang != s.language.lower():
                    continue
            else:
                # Фикс багов №5 и №6: Безопасное форматирование строк вместо сложения через оператор "+"
                search_target = f"{safe_text} {safe_note} {s.tags or ''} {s.category} {s.sub_category or ''}".lower()
                if query not in search_target: 
                    continue

        html += f"""
        <div id="snippet-{s.id}" class="bg-gray-900/60 p-6 rounded-3xl border border-gray-800/80 shadow-2xl group hover:border-teal-500/40 transition-all backdrop-blur-md">
            <div class="flex justify-between items-start mb-3">
                <div class="flex flex-col gap-1">
                    <span class="text-[10px] font-mono text-teal-400 uppercase tracking-widest">{s.category} // {s.sub_category}</span>
                    {f'<span class="text-[9px] text-purple-400 font-mono">🔗 NEXUS LINK ID: {s.parent_snippet_id}</span>' if s.parent_snippet_id else ''}
                    <div class="flex gap-1 text-[10px] text-emerald-400 font-mono">
                        {s.tags if s.tags else ""}
                    </div>
                </div>
                <button hx-delete="/snippets/delete/{s.id}" hx-target="#snippet-{s.id}" hx-swap="outerHTML swap:0.4s" class="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 transition-all cursor-pointer">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
            </div>
            
            {f'<div class="mb-4 rounded-2xl overflow-hidden border border-gray-800"><img src="{s.image_url}" class="w-full h-auto object-cover opacity-80 hover:opacity-100 transition-opacity"/></div>' if s.image_url else ''}
            
            <p class="text-gray-200 whitespace-pre-wrap text-sm leading-relaxed mb-4 font-sans">{safe_text}</p>
            
            {f'<div class="mt-3 p-3 bg-black/40 rounded-xl border-l-2 border-teal-500/60"><p class="text-xs text-gray-400 italic">💡 {safe_note}</p></div>' if safe_note else ''}
            
            {f'<div class="mt-2 text-[9px] text-amber-400 font-mono">🔔 Напоминание: {s.reminder_at.strftime("%d.%m.%Y %H:%M")}</div>' if s.reminder_at else ''}

            <div class="mt-4 pt-3 border-t border-gray-800/60 flex justify-between items-center text-[9px] text-gray-600 font-mono">
                <span>{s.created_at.strftime('%d.%m.%Y')}</span>
                <span class="uppercase tracking-tighter text-teal-600/60">RellixCrypt Port: {s.id} // v{s.version}</span>
            </div>
        </div>
        """
    return HTMLResponse(content=html or "<div class='col-span-full text-center py-20 text-gray-600 italic font-mono'>Ничего не найдено в archives... 🕵️‍♂️</div>")


@router.get("/export")
async def export_snippets(request: Request, session: AsyncSession = Depends(get_session)):
    user_id = get_current_user_from_cookie(request)
    if not user_id: 
        return Response(status_code=401)

    user = await session.get(User, user_id)
    if not user:
        return Response(status_code=404)

    statement = select(Snippet).where(Snippet.user_id == user.id)
    query_result = await session.execute(statement)
    snippets = query_result.scalars().all()

    export_data = []
    for s in snippets:
        content = decrypt_data(s.content, user.encryption_salt, s.category) or "[Decryption Error]"
        note = decrypt_data(s.note, user.encryption_salt, s.category) if s.note else ""

        export_data.append({
            "title": s.title,
            "category": s.category,
            "sub_category": s.sub_category,
            "content": content,
            "note": note,
            "tags": s.tags,
            "version": s.version,
            "created_at": s.created_at.isoformat()
        })

    json_str = json.dumps(export_data, indent=4, ensure_ascii=False)
    buffer = io.BytesIO(json_str.encode("utf-8"))
    
    return StreamingResponse(
        buffer, 
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=rellixcore_backup.json"}
    )


@router.delete("/delete/{snippet_id}")
async def delete_snippet(snippet_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    user_id = get_current_user_from_cookie(request)
    snippet = await session.get(Snippet, snippet_id)
    
    if not snippet or snippet.user_id != user_id: 
        return Response(status_code=403)
        
    await session.delete(snippet)
    await session.commit()
    return HTMLResponse(content="")