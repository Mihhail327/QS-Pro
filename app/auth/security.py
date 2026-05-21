import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request
from jose import jwt, JWTError

from securitycore import hash_password, verify_password
from securitycore.analysis.password_analyzer import password_analyzer

# Считываем конфигурацию из Docker-окружения
SECRET_KEY = os.getenv("SECRET_KEY", "GITS_SECTION_9_ULTRA_SECRET_2026_KEY_NEXO")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))


def hash_user_password(password: str) -> str:
    return hash_password(password)


def verify_user_password(plain_password: str, hashed_password: str) -> bool:
    return verify_password(plain_password, hashed_password)


def validate_password_strength(password: str) -> bool:
    """
    Анализ сложности
    Пропускаем пароль в базу, только если его brute_force_bits >= 45 (не weak)
    и он проходит базовые проверки.
    """
    try:
        analysis = password_analyzer(password)
        
        # Отсекаем слабые пароли на основе битов стойкости из твоего SDK
        if analysis and isinstance(analysis, dict):
            # Запрещаем регистрацию, если сила пароля "weak"
            if analysis.get("strength") == "weak" or analysis.get("brute_force_bits", 0) < 45:
                return False
            return True
            
        return len(password) >= 8
    except Exception:
        # Безопасный фоллбэк на случай непредвиденного сбоя импортов
        return len(password) >= 8


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_from_cookie(request: Request) -> Optional[int]:
    token = request.cookies.get("access_token")
    if not token:
        return None
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        
        if user_id is None:
            return None
            
        return int(user_id)
    except (JWTError, ValueError, TypeError):
        return None