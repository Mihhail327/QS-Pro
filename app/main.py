import logging
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database.config import create_db_and_tables
from app.routes import auth, snippets, home
from app.core.middlewares import error_handling_middleware, rellix_security_audit_layer
from app.core.logging_config import setup_logging_and_telemetry

app = FastAPI(
    title="RellixCore :: QuickSnippet Pro",
    description="The Secure Cyber-Baroque Vault. Engineered by NexO_.",
    version="1.0.0-Senior",
    docs_url="/docs"
)

setup_logging_and_telemetry(app)

# 🛡️ Активируем слои защиты и перехвата ошибок
app.middleware("http")(error_handling_middleware)
app.middleware("http")(rellix_security_audit_layer)

# 🔌 Маршруты для PWA (должны отдаваться от корня для верной области видимости SW)
@app.get("/sw.js")
async def serve_sw():
    return FileResponse("app/static/js/sw.js", media_type="application/javascript")

@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse("app/static/js/manifest.json", media_type="application/json")

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
     R E L L I X   C O R E
    ===================================================
    :: QuickSnippet Pro Framework v1.0.0 ::
    :: Authored by NexO_ | Distributed by RellixCore ::
    ===================================================
    """)
    await create_db_and_tables()