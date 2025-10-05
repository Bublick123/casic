from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .database import engine, Base
from api.endpoints import router as admin_router

app = FastAPI(title="Casino Admin Service", version="1.0.0")



# Подключаем роуты
app.include_router(admin_router)

@app.get("/")
async def root():
    return {"message": "Casino Admin Service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}