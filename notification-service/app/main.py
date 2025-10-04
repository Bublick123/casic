from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
import asyncio

from app.database import Base, engine
from app.api.endpoints import router as notifications_router
from app.queues.processor import notification_processor

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        # Создаем таблицы
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully!")
        
        # Запускаем процессор уведомлений
        from app.database import SessionLocal
        db = SessionLocal()
        asyncio.create_task(notification_processor.process_queue(db))
        logger.info("✅ Notification processor started!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup error: {str(e)}")
        raise
    
    finally:
        # Shutdown
        await notification_processor.stop()
        logger.info("✅ Notification service stopped")

app = FastAPI(
    title="Notification Service",
    description="Microservice for sending email and real-time notifications",
    version="1.0.0",
    lifespan=lifespan
)

# Подключаем роутеры
app.include_router(notifications_router)

@app.get("/")
async def root():
    return {"message": "Notification Service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "notifications"}