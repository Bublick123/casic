from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from .config import settings
import re
import random

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # Ограничиваем длину пароля до 72 байт для bcrypt
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return pwd_context.hash(password_bytes)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Аналогично ограничиваем при проверке
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return pwd_context.verify(password_bytes, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

from .database import SessionLocal
from . import models

def is_token_blacklisted(token: str) -> bool:
    db = SessionLocal()
    try:
        blacklisted = db.query(models.BlacklistedToken).filter(
            models.BlacklistedToken.token == token
        ).first()
        return blacklisted is not None
    finally:
        db.close()

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # 7 дней
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# Валидация пароля 
def validate_password_complexity(password: str) -> bool:
    """Проверяет сложность пароля"""
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):  # Хотя бы одна заглавная
        return False
    if not re.search(r"[a-z]", password):
        return False  
    if not re.search(r"\d", password):     # Хотя бы одна цифра
        return False
    if not re.search(r"[!@#$%^&*()_+]", password):  # Хотя бы один спецсимвол
        return False
    # Дополнительная проверка на максимальную длину для bcrypt
    if len(password.encode('utf-8')) > 72:
        return False
    return True

# Генерация кода подтверждения
def generate_verification_code() -> str:
    """Генерирует 6-значный код подтверждения"""
    return str(random.randint(100000, 999999))