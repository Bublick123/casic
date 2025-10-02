from fastapi import FastAPI
from .database import Base, engine
from .api.endpoints import router as analytics_router

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Analytics Service",
    description="Microservice for casino analytics and metrics",
    version="1.0.0"
)

# Подключаем роутеры
app.include_router(analytics_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "analytics"}

@app.get("/")
async def root():
    return {"message": "Analytics Service is running"}