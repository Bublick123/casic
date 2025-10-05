from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
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

templates = Jinja2Templates(directory="app/templates")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "game"}

@app.get("/")
async def root():
    return {"message": "Game Service is running"}

# Простой импорт роутера 
# Рулетка
from .roulette import router as roulette_router
app.include_router(roulette_router)
# Слоты
from .slots import router as slots_router 
app.include_router(slots_router) 
#БлэкДжек
from .blackjack import router as blackjack_router
app.include_router(blackjack_router)

# Minimal UI endpoints
@app.get("/ui/login", response_class=HTMLResponse)
async def ui_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/ui/games", response_class=HTMLResponse)
async def ui_games(request: Request):
    return templates.TemplateResponse("games.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)