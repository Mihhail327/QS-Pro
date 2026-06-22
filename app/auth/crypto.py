import base64
import os
from hashlib import pbkdf2_hmac
from typing import Optional
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from app.core.exceptions import SecurityBreachException

# Базовый мастер-ключ шлюза, прокинутый через Docker-окружение
SECRET_KEY = os.getenv("SECRET_KEY", "GITS_SECTION_9_ULTRA_SECRET_2026_KEY_NEXO").encode()


def _derive_shifted_key(user_salt: str, category: str) -> bytes:
    context_salt = f"{user_salt}:{category}".encode()
    return pbkdf2_hmac(
        hash_name="sha256",
        password=SECRET_KEY,
        salt=context_salt,
        iterations=10_000,
        dklen=32
    )


def encrypt_data(plain_text: str, user_salt: str, category: str) -> str:
    """
    Аутентифицированное шифрование данных AES-256-GCM.
    Возвращает строку в формате base64: IV (12B) + TAG (16B) + CIPHERTEXT.
    """
    if not plain_text:
        return ""

    derived_key = _derive_shifted_key(user_salt, category)
    
    # Генерируем 12 байт для IV (nonce) под стандарт GCM
    static_nonce = get_random_bytes(12)
    
    cipher = AES.new(derived_key, AES.MODE_GCM, nonce=static_nonce)
    
    ciphertext, tag = cipher.encrypt_and_digest(plain_text.encode("utf-8"))
    
    # ИСПРАВЛЕНИЕ БАГА: Используем static_nonce (который строго bytes) 
    # вместо cipher.nonce (который возвращает memoryview)
    packed_data = static_nonce + tag + ciphertext
    return base64.b64encode(packed_data).decode("utf-8")


def decrypt_data(crypto_text: str, user_salt: str, category: str) -> Optional[str]:
    """
    Расшифровка и тотальная проверка целостности контейнера AES-256-GCM.
    """
    if not crypto_text:
        return ""

    try:
        raw_data = base64.b64decode(crypto_text.encode("utf-8"))
        
        nonce = raw_data[:12]
        tag = raw_data[12:28]
        ciphertext = raw_data[28:]
        
        derived_key = _derive_shifted_key(user_salt, category)
        
        cipher = AES.new(derived_key, AES.MODE_GCM, nonce=nonce)
        
        decrypted_bytes = cipher.decrypt_and_verify(ciphertext, tag)
        return decrypted_bytes.decode("utf-8")
        
    except (ValueError, KeyError, TypeError) as e:
        print(f"⚠️ [SECURITY CRITICAL] Попытка подмены зашифрованных данных! Контекст: {e}")
        raise SecurityBreachException("Integrity check failed: ciphertext tampered or key shifting mismatch.") from e