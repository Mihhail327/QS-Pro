from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.config import get_session
from app.models.snippet import User
from app.auth.security import get_current_user_from_cookie

router = APIRouter(tags=["home"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, session: AsyncSession = Depends(get_session)):
    user_id = get_current_user_from_cookie(request)
    
    if not user_id:
        return RedirectResponse(url="/auth/login")
    
    user = await session.get(User, user_id)
    
    if not user:
        response = RedirectResponse(url="/auth/login")
        response.delete_cookie("access_token")
        return response

    return templates.TemplateResponse(
        request=request, name="index.html", context={"user": user}
    )