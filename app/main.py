import logging
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database.config import create_db_and_tables
from app.routes import auth, snippets, home
from app.core.middlewares import error_handling_middleware, rellix_security_audit_layer

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="RellixCore :: QuickSnippet Pro",
    description="The Secure Cyber-Baroque Vault. Engineered by NexO_.",
    version="1.0.0-Senior",
    docs_url="/docs"
)

# 🛡️ Активируем слои защиты и перехвата ошибок
app.middleware("http")(error_handling_middleware)
app.middleware("http")(rellix_security_audit_layer)

# 🔌 Подключаем кроссплатформенные REST-роутеры
app.include_router(home.router)
app.include_router(auth.router)
app.include_router(snippets.router)

# 📁 Монтируем статику
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
async def on_startup():
    print("""
    ===================================================
     ██████╗ ███████╗██╗     ██╗    ██╗██╗  ██╗
     ██╔══██╗██╔════╝██║     ██║    ██║╚██╗██╔╝
     ██████╔╝█████╗  ██║     ██║    ██║ ╚███╔╝ 
     ██╔══██╗██╔══╝  ██║     ██║    ██║ ██╔██╗ 
     ██║  ██║███████╗███████╗███████╗██║██╔╝ ██╗
     ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝╚═╝  ╚═╝ CORE
    ===================================================
    :: QuickSnippet Pro Framework v1.0.0 ::
    :: Authored by NexO_ | Distributed by RellixCore ::
    ===================================================
    """)
    await create_db_and_tables()