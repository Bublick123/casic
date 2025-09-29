from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
Base = declarative_base()
# Модель Пользователя
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True) #id пользователя
    login = Column(String, unique=True, index=True) #логин пользователя
    email = Column(String, unique=True, index=True) #почта пользователя
    hashed_password = Column(String) #хешированый пароль 
    created_at = Column(DateTime, default=datetime.utcnow)  # Дата регистрации пользователя
    login_count = Column(Integer, default=0)               # Счетчик логинов пользователя
    last_login = Column(DateTime, nullable=True)           # Последний логин пользователя
    role = Column(String, default="user")  # ← Роль пользователя
    email_verified = Column(Boolean, default=False)  # Подтвержден ли email
    verification_code = Column(String, nullable=True) # Код подтверждения


class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    blacklisted_at = Column(DateTime, default=datetime.utcnow)    


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)  
