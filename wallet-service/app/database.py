from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
import os

# Берем URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://casino_user:casino_password@wallet-postgres:5432/wallet_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()