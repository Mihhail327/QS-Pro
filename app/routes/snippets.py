import io
import os
import time
import json
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image

from app.database.config import get_session
from app.models.snippet import Snippet, User
from app.auth.security import get_current_user_from_cookie
from app.auth.crypto import decrypt_data
from securitycore import input_sanitizer

# Импортируем наши новые микро-сервисы
from app.services.snippet_service import create_new_snippet, get_user_snippets
from app.services.html_renderer import render_snippet_cards

router = APIRouter(prefix="/snippets", tags=["snippets"])

async def secure_image_save(upload_file: UploadFile, upload_dir: str = "app/static/uploads") -> str:
    """Стерилизация и сжатие изображения в WebP"""
    os.makedirs(upload_dir, exist_ok=True)
    
    image_bytes = await upload_file.read()
    img = Image.open(io.BytesIO(image_bytes))
    
    # Принудительная конвертация в RGB убивает любые скрытые данные в альфа-каналах
    if img.mode != "RGB":
        img = img.convert("RGB")
        
    safe_filename = f"cyber_{int(time.time())}_{os.urandom(4).hex()}.webp"
    filepath = f"{upload_dir}/{safe_filename}"
    
    img.save(filepath, format="WEBP", quality=80, method=6)
    return f"/static/uploads/{safe_filename}"


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
        return HTMLResponse(content="<span class='text-red-400'>❌ Ошибка сессии.</span>", status_code=401)
    
    user = await session.get(User, user_id)
    if not user or user.id is None:
        return HTMLResponse(content="<span class='text-red-400'>❌ Ошибка профиля.</span>", status_code=401)

    clean_title = str(input_sanitizer(content[:30] + "..."))

    # 1. СТЕРИЛИЗАЦИЯ ИЗОБРАЖЕНИЯ
    final_image_url = None
    if image and image.filename:
        try:
            final_image_url = await secure_image_save(image)
        except Exception:
            return HTMLResponse(content="<span class='text-red-400 font-mono'>❌ Ошибка медиа: неверный формат</span>", status_code=400)

    # 2. ВАЛИДАЦИЯ СВЯЗИ (NEXUS LINKS) ДЛЯ ЗАЩИТЫ ОТ BOLA И КРАША БД
    if parent_snippet_id:
        parent_snippet = await session.get(Snippet, parent_snippet_id)
        if not parent_snippet or parent_snippet.user_id != user.id:
            return HTMLResponse(content="<span class='text-red-400 font-mono'>❌ Ошибка: Родоначальный сниппет не найден или недоступен</span>", status_code=400)

    # 3. ПЕРЕХОД К СОЗДАНИЮ СНИППЕТА В СЕРВИСЕ
    await create_new_snippet(
        session, user, category, content, sub_category, note, 
        tags, parent_snippet_id, reminder_at, final_image_url, clean_title
    )
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
        return HTMLResponse(content="<p class='text-gray-500 font-mono'>Авторизуйтесь.</p>")
    
    user = await session.get(User, user_id)
    if not user or user.id is None:
        return HTMLResponse(content="<p class='text-gray-500 font-mono'>Ошибка профиля.</p>")
    
    raw_snippets = await get_user_snippets(session, user.id, category)
    html_content = render_snippet_cards(raw_snippets, user.encryption_salt, q)
    
    return HTMLResponse(content=html_content)


@router.get("/export")
async def export_snippets(request: Request, session: AsyncSession = Depends(get_session)):
    user_id = get_current_user_from_cookie(request)
    if not user_id:
        return Response(status_code=401)
        
    user = await session.get(User, user_id)
    if not user or user.id is None:
        return Response(status_code=404)

    snippets = await get_user_snippets(session, user.id, "all")
    
    export_data = [{
        "title": s.title, 
        "category": s.category, 
        "sub_category": s.sub_category,
        "content": decrypt_data(s.content, user.encryption_salt, s.category) or "",
        "note": decrypt_data(s.note, user.encryption_salt, s.category) if s.note else "",
        "tags": s.tags, 
        "version": s.version, 
        "created_at": s.created_at.isoformat(),
        "image_url": s.image_url  # На всякий случай добавил в экспорт
    } for s in snippets]

    buffer = io.BytesIO(json.dumps(export_data, indent=4, ensure_ascii=False).encode("utf-8"))
    return StreamingResponse(
        buffer, 
        media_type="application/json", 
        headers={"Content-Disposition": "attachment; filename=rellix_backup.json"}
    )


@router.delete("/delete/{snippet_id}")
async def delete_snippet(snippet_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    user_id = get_current_user_from_cookie(request)
    if not user_id:
        return Response(status_code=401)

    snippet = await session.get(Snippet, snippet_id)
    if not snippet or snippet.user_id != user_id:
        return Response(status_code=403)
        
    # 1. Зачистка файловой системы (уничтожение скриншота)
    if snippet.image_url:
        # В базе ссылка лежит как "/static/uploads/...", 
        # а на диске путь начинается с "app/static/uploads/..."
        # Просто склеиваем "app" и URL
        file_path = f"app{snippet.image_url}"
        
        try:
            # Проверяем, существует ли файл, чтобы система не упала от ошибки
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"[🗑️ СИСТЕМА] Файл уничтожен: {file_path}")
        except Exception as e:
            # Если файл кто-то уже удалил руками — просто игнорируем
            print(f"[⚠️ СИСТЕМА] Ошибка при удалении файла: {e}")

    # 2. Удаление самого сниппета из базы данных
    await session.delete(snippet)
    await session.commit()
    
    return HTMLResponse(content="")