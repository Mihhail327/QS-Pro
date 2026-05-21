import secrets
from fastapi import APIRouter, Depends, Request, Response, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

# Инфраструктура ядра RellixCore
from app.database.config import get_session
from app.models.snippet import User
from app.auth.security import (
    get_current_user_from_cookie,
    hash_user_password,
    verify_user_password,
    validate_password_strength,
    create_access_token,
)


from securitycore import input_sanitizer
from securitycore.analysis.password_analyzer import password_analyzer

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


@router.post("/register")
async def register(
    username: str = Form(...), 
    password: str = Form(...), 
    is_dev: bool = Form(False),
    session: AsyncSession = Depends(get_session)
):
    """
    Асинхронная регистрация с тотальным анализом энтропии
    пароля через встроенный SecurityCore SDK.
    """
    username = username.strip()
    
    # Стерилизация и базовая проверка длины логина
    if len(username) < 3 or len(username) > 20:
        return HTMLResponse(content="<span class='text-red-400 font-mono'>❌ Имя должно быть от 3 до 20 символов</span>")
    
    # 🧠 ИНТЕГРАЦИЯ SECURITYCORE: Проверяем пароль на математическую стойкость
    if not validate_password_strength(password):
        # Если пароль заблокирован, вытягиваем рекомендации из твоего же анализатора
        analysis = password_analyzer(password)
        recommendation = "Пароль слишком слаб (низкая энтропия)."
        if analysis and isinstance(analysis, dict) and analysis.get("recommendations"):
            recommendation = analysis["recommendations"][0]  # Берем первый критический совет
            
        return HTMLResponse(content=f"<span class='text-red-400 font-mono'>❌ {recommendation}</span>")

    # Асинхронная проверка: занято ли имя в PostgreSQL
    statement = select(User).where(User.username == username)
    query_result = await session.execute(statement)
    if query_result.scalars().first():
        return HTMLResponse(content="<span class='text-red-400 font-mono'>❌ Это секретное имя уже занято</span>")

    # Генерация уникальной крипто-соли пользователя для будущих Key Shifting операций в AES-GCM
    salt = secrets.token_hex(16)
    
    new_user = User(
        username=username,
        hashed_password=hash_user_password(password),  # Твой Argon2id
        is_dev=is_dev,
        encryption_salt=salt
    )
    
    session.add(new_user)
    await session.commit()
    return HTMLResponse(content="<span class='text-emerald-400 font-mono'>✅ Регистрация успешна! Введите данные для входа.</span>")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="auth.html", context={})


@router.post("/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    if not username or not password:
        return HTMLResponse(content="<span class='text-red-400 font-mono'>❌ Заполните все поля терминала</span>")

    # Асинковски ищем сущность в Postgres
    statement = select(User).where(User.username == username.strip())
    query_result = await session.execute(statement)
    user = query_result.scalars().first()
    
    # Защита от тайминг-атак: сверка Argon2id
    if not user or not verify_user_password(password, user.hashed_password):
        return HTMLResponse(content="<span class='text-red-400 font-mono'>❌ Неверный логин или крипто-ключ</span>")

    if user.id is None:
        return HTMLResponse(content="<span class='text-red-400 font-mono'>❌ Критическая ошибка идентификатора</span>")

    # Создаем индустриальный JWT-токен
    token = create_access_token(data={"sub": str(user.id)})
    
    # Упаковываем сессию в бронированную HttpOnly куку
    response.set_cookie(
        key="access_token", 
        value=token, 
        httponly=True, 
        samesite="lax",  # Строгий барьер против CSRF-атак
        secure=False     # Выставить в True при наличии TLS/HTTPS на проде
    )
    
    # Приказываем HTMX совершить мгновенный редирект на командный мостик
    response.headers["HX-Redirect"] = "/"
    return HTMLResponse(content="<span class='text-teal-400 font-mono'>Авторизация пройдена. Вход...</span>")


@router.get("/status", response_class=HTMLResponse)  
async def get_auth_status(request: Request, session: AsyncSession = Depends(get_session)):
    user_id = get_current_user_from_cookie(request)
    
    if not user_id:
        return HTMLResponse(
            content='<a href="/auth/login" class="bg-teal-600 hover:bg-teal-700 text-white text-xs font-mono py-2 px-6 rounded-xl transition-all shadow-lg inline-block">ВОЙТИ В СЕЙФ</a>'
        )
    
    user = await session.get(User, user_id)
    if user and user.id is not None:
        is_dev_str = "dev" if user.is_dev else "user"
        
        # 🛡️ ПРЕВЕНТИВНЫЙ ЩИТ: Санитизируем ник перед выводом в DOM, исключая Stored XSS
        safe_username = str(input_sanitizer(user.username))
        
        return HTMLResponse(content=f'''
            <div class="flex items-center gap-3" x-data="{{ role: \'{is_dev_str}\' }}">
                <span class="text-teal-400 text-xs font-mono">● {safe_username}</span>
                <button hx-post="/auth/logout" hx-target="body" class="text-[10px] text-gray-500 hover:text-red-400 font-mono uppercase tracking-widest transition cursor-pointer">Выйти</button>
            </div>
        ''')
    return HTMLResponse(content="")


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.headers["HX-Redirect"] = "/"
    return HTMLResponse(content="Выход из системы...")