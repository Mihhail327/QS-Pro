import logging
import os
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
# 🔌 ИСПРАВЛЕНИЕ: Импортируем асинковую сессию
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user_from_cookie
from app.database.config import create_db_and_tables, get_session
from app.models.snippet import User
from app.routes import auth, snippets

from securitycore.integrations import SecurityAuditMiddleware

# Логирование инфраструктуры
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RellixCore :: QuickSnippet Pro",
    description="The Secure Cyber-Baroque Vault. Engineered by NexO_.",
    version="1.0.0-Senior",
    docs_url="/docs"  # Защищенный Swagger-интерфейс шлюза
)

# АКТИВИРУЕМ ТИТАНОВЫЙ ЩИТ: Интеграция твоего SecurityCore SDK
audit_shield = SecurityAuditMiddleware()

@app.middleware("http")
async def rellix_security_audit_layer(request, call_next):
    """
    Прослойка интеграции SecurityCore SDK.
    Бесшовно передает контекст запроса в твой кастомный метод __call__.
    """
    return await audit_shield(request, call_next)

# Подключаем кроссплатформенные REST-роутеры
app.include_router(auth.router)
app.include_router(snippets.router)


@app.on_event("startup")
async def on_startup():
    print("""
    ===================================================
     ██████╗ ███████╗██╗     ██╗     ██╗██╗  ██╗
     ██╔══██╗██╔════╝██║     ██║     ██║╚██╗██╔╝
     ██████╔╝█████╗  ██║     ██║     ██║ ╚███╔╝ 
     ██╔══██╗██╔══╝  ██║     ██║     ██║ ██╔██╗ 
     ██║  ██║███████╗███████╗███████╗██║██╔╝ ██╗
     ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝ CORE
    ===================================================
    :: QuickSnippet Pro Framework v1.0.0 ::
    :: Authored by NexO_ | Distributed by RellixCore ::
    ===================================================
    """)
    # Автоматическая ковка структуры таблиц в PostgreSQL
    await create_db_and_tables()


# Статика и шаблоны
templates = Jinja2Templates(directory="app/templates")

if not os.path.exists("app/static"):
    os.makedirs("app/static")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session: AsyncSession = Depends(get_session)): # Поменяли тип на AsyncSession
    user_id = get_current_user_from_cookie(request)
    
    # Если не авторизован — перенаправляем на страницу входа
    if not user_id:
        return RedirectResponse(url="/auth/login")
    
    # 🛠️ ИСПРАВЛЕНИЕ: Асинхронно достаем пользователя из PostgreSQL через await
    user = await session.get(User, user_id)
    
    # Защита сессии: если ID в куке устарел или пользователя удалили из БД
    if not user:
        response = RedirectResponse(url="/auth/login")
        response.delete_cookie("access_token")  # Аннигилируем битую куку
        return response

    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"user": user}
    )


# Глобальный обработчик ошибок (Инфраструктурный Middleware перехвата)
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    if request.url.path.startswith("/static"):
        return await call_next(request)
    
    try:
        return await call_next(request)
    except Exception as e:
        # 🎯 ИСПРАВЛЕНИЕ: Логируем аварию конкретного продукта QS Pro!
        logger.error(f"⚠️ Глобальный сбой шлюза QuickSnippet Pro: {e}", exc_info=True)
        
        # Если авария произошла во время реактивного HTMX запроса
        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content="<div class='p-4 bg-red-900/40 border border-red-500 text-red-200 rounded-xl font-bold'>"
                        "⚠️ Ошибка защищенного шлюза QS Pro. Попробуйте повторить операцию."
                        "</div>"
            )
        
        # Безопасный фоллбэк: отдаем главный интерфейс
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={"hasError": True, "user": None}
        )