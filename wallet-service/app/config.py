import os

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-here")  # ТОТ ЖЕ КЛЮЧ!
    ALGORITHM = "HS256"

settings = Settings()