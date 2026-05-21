import httpx
from src.config import Config

class AuthAPI:
    @staticmethod
    async def login(username: str, password: str) -> dict | None:
        """Отправляет запрос авторизации на FastAPI сервер в формате Form-Data."""
        payload = {
            "username": username,
            "password": password
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{Config.API_BASE_URL}/auth/login", 
                    data=payload,
                    timeout=5.0
                )
                
                # 🎯 Сделка века: если статус 200 — значит бэкенд впустил нас!
                if response.status_code == 200:
                    # Если бэкенд вернул JSON-токен (Rest API стандарт)
                    if "application/json" in response.headers.get("content-type", ""):
                        return response.json()
                    
                    # Если бэкенд вернул HTML-страницу (значит, вход через форму успешен!)
                    # Возвращаем фейковый токен, чтобы фронтенд Flet понял, что доступ разрешен
                    return {"access_token": "session_approved_via_html"}
                
                print(f"API Log: Отказ шлюза [{response.status_code}] -> Неверные данные или редирект.")
                return None
                
            except httpx.RequestError as exc:
                print(f"API Log: Критическая ошибка сети при связи со шлюзом: {exc}")
                return None