from fastapi import FastAPI
import logging
from .database import engine, Base

# Создаем таблицы
Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Game Service API",
    description="Microservice for casino games", 
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "game"}

@app.get("/")
async def root():
    return {"message": "Game Service is running"}

# Простой импорт роутера
from .roulette import router as roulette_router
app.include_router(roulette_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)