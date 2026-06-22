import json
from fastapi import APIRouter, Depends, Request, Response, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

# Инфраструктура
from app.database.config import get_session
from app.models.snippet import User
from app.auth.security import get_current_user_from_cookie, create_access_token
from app.services.auth_service import register_user, authenticate_user, get_user_status_data

from securitycore import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")

@router.post("/register")
async def register(
    username: str = Form(...), 
    password: str = Form(...), 
    is_dev: bool = Form(False),
    session: AsyncSession = Depends(get_session)
):
    success, message = await register_user(username.strip(), password, is_dev, session)
    
    if not success:
        return HTMLResponse(content=f"<span class='text-red-400 font-mono'>❌ {message}</span>")
    return HTMLResponse(content=f"<span class='text-electric font-mono'>✅ {message}</span>")

@router.post("/change-password")
async def change_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    user_id = get_current_user_from_cookie(request)
    if not user_id:
        return HTMLResponse(content="<span class='text-red-500'>❌ Ошибка доступа.</span>", status_code=401)
    
    user = await session.get(User, user_id)
    if not user:
        return HTMLResponse(content="<span class='text-red-500'>❌ Пользователь не найден.</span>", status_code=404)

    # ИСПОЛЬЗУЕМ ВАШ SecurityCore:
    # verify_password из SecurityCore уже знает, как работать с Argon2 и legacy форматами
    if not verify_password(old_password, user.hashed_password):
        return HTMLResponse(content="<span class='text-red-500'>❌ Неверный текущий ключ.</span>")
    
    if old_password == new_password:
        return HTMLResponse(content="<span class='text-yellow-500'>⚠️ Новый ключ совпадает со старым.</span>")

    # Хэшируем новым методом из твоего SDK
    user.hashed_password = hash_password(new_password)
    session.add(user)
    await session.commit()

    return HTMLResponse(content="<span class='text-acid'>✔ Ключ успешно перезаписан через SecurityCore!</span>")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="auth.html", context={})

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    user, error_msg = await authenticate_user(username.strip(), password, session)
    
    if not user:
        # Для Flet-клиента или API-запросов отдаем JSON
        if "application/json" in request.headers.get("accept", "").lower() or not request.headers.get("hx-request"):
            return Response(content=json.dumps({"detail": error_msg}), media_type="application/json", status_code=401)
        return HTMLResponse(content=f"<span class='text-red-400 font-mono'>❌ {error_msg}</span>")

    # Создаем токен
    token = create_access_token(data={"sub": str(user.id)})
    
    # Для Flet-клиента или API-запросов отдаем JSON
    if "application/json" in request.headers.get("accept", "").lower() or not request.headers.get("hx-request"):
        return {"access_token": token, "token_type": "bearer"}

    # 1. Формируем финальный объект ответа
    final_response = HTMLResponse(
        content="<span class='text-electric font-mono shadow-electric'>Авторизация пройдена... Вход в ядро.</span>"
    )
    
    # 2. Вешаем куки
    final_response.set_cookie(
        key="access_token", value=token, httponly=True, samesite="lax", secure=False 
    )
    
    # 3. Жестко приказываем HTMX сделать редирект
    final_response.headers["HX-Redirect"] = "/"
    
    return final_response

    
@router.get("/status", response_class=HTMLResponse)  
async def get_auth_status(request: Request, session: AsyncSession = Depends(get_session)):
    user_id = get_current_user_from_cookie(request)
    
    if not user_id:
        return HTMLResponse(
            content='<a href="/auth/login" class="bg-electric/10 hover:bg-electric/20 border border-electric text-electric text-xs font-mono py-2 px-6 rounded-xl transition-all shadow-neon inline-block uppercase tracking-widest">ВОЙТИ В СЕЙФ</a>'
        )
    
    data = await get_user_status_data(user_id, session)
    if data:
        safe_username, is_dev_str = data
        return HTMLResponse(content=f'''
            <div class="flex items-center gap-3" x-data="{{ role: \'{is_dev_str}\' }}">
                <span class="text-electric text-xs font-mono drop-shadow-[0_0_5px_rgba(0,242,254,0.8)]">● {safe_username}</span>
                <button hx-post="/auth/logout" hx-target="body" class="text-[10px] text-gray-500 hover:text-red-500 font-mono uppercase tracking-widest transition cursor-pointer">Выйти</button>
            </div>
        ''')
        
    return HTMLResponse(content="")

@router.post("/logout")
async def logout():
    # Создаем объект ответа
    response = Response(status_code=204) # 204 No Content — лучший статус для таких операций
    
    # Удаляем куку
    response.delete_cookie("access_token")
    
    # Приказываем HTMX перенаправить пользователя на главную
    response.headers["HX-Redirect"] = "/"
    
    return response