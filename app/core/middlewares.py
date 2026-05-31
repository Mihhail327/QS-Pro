import logging
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from securitycore.integrations import SecurityAuditMiddleware

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")

# Твой титановый щит
audit_shield = SecurityAuditMiddleware()

async def rellix_security_audit_layer(request: Request, call_next):
    """Прослойка интеграции SecurityCore SDK."""
    return await audit_shield(request, call_next)

async def error_handling_middleware(request: Request, call_next):
    """Глобальный обработчик ошибок (Инфраструктурный Middleware перехват)."""
    if request.url.path.startswith("/static"):
        return await call_next(request)
    
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(f"⚠️ Глобальный сбой шлюза QuickSnippet Pro: {e}", exc_info=True)
        
        if request.headers.get("HX-Request"):
            return HTMLResponse(
                content="<div class='p-4 bg-red-900/40 border border-red-500 text-red-200 rounded-xl font-mono text-xs'>"
                        "⚠️ Ошибка защищенного шлюза QS Pro. Повторите операцию."
                        "</div>"
            )
        
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={"hasError": True, "user": None}
        )