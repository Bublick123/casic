import asyncio
import logging
from sqlalchemy.orm import Session
from datetime import datetime
from ..models import Notification
from ..email.sender import email_sender

logger = logging.getLogger(__name__)

class NotificationProcessor:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.is_running = False
    
    async def add_notification(self, notification_data: dict):
        """Добавление уведомления в очередь"""
        await self.queue.put(notification_data)
        logger.info(f"Notification added to queue: {notification_data['type']}")
    
    async def process_queue(self, db: Session):
        """Обработка очереди уведомлений"""
        self.is_running = True
        logger.info("Notification processor started")
        
        while self.is_running:
            try:
                # Ждем уведомление (с таймаутом для graceful shutdown)
                try:
                    notification_data = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Обрабатываем уведомление
                await self.process_notification(db, notification_data)
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing notification queue: {str(e)}")
    
    async def process_notification(self, db: Session, data: dict):
        """Обработка одного уведомления"""
        try:
            notification = Notification(
                user_id=data["user_id"],
                type=data["type"],
                title=data.get("title", ""),
                message=data.get("message", ""),
                status="pending"
            )
            db.add(notification)
            db.commit()
            
            # Отправляем в зависимости от типа
            if data["type"] == "email":
                success = await self.send_email_notification(data)
            elif data["type"] == "websocket":
                success = await self.send_websocket_notification(data)
            else:
                success = False
            
            # Обновляем статус
            notification.status = "sent" if success else "failed" # type: ignore
            notification.sent_at = datetime.utcnow() if success else None# type: ignore
            db.commit()
            
            logger.info(f"Notification processed: {data['type']}, success: {success}")
            
        except Exception as e:
            logger.error(f"Error processing notification: {str(e)}")
            db.rollback()
    
    async def send_email_notification(self, data: dict) -> bool:
        """Отправка email уведомления"""
        try:
            template_name = data.get("template", "generic")
            context = data.get("context", {})
            
            html_content = email_sender.render_template(template_name, context)
            if not html_content:
                html_content = f"<h1>{data.get('title', 'Notification')}</h1><p>{data.get('message', '')}</p>"
            
            # В реальном проекте здесь был бы реальный email
            # Для демо просто логируем
            logger.info(f"📧 EMAIL SENT: To user {data['user_id']}, Subject: {data.get('title', 'Notification')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    async def send_websocket_notification(self, data: dict) -> bool:
        """Отправка WebSocket уведомления"""
        try:
            from ..websocket.manager import manager
            
            message = {
                "type": "notification",
                "title": data.get("title", ""),
                "message": data.get("message", ""),
                "timestamp": datetime.utcnow().isoformat(),
                "data": data.get("data", {})
            }
            
            await manager.send_personal_message(message, data["user_id"])
            logger.info(f"🔌 WEBSOCKET SENT: To user {data['user_id']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending websocket notification: {str(e)}")
            return False
    
    async def stop(self):
        """Остановка процессора"""
        self.is_running = False
        logger.info("Notification processor stopped")

# Глобальный процессор
notification_processor = NotificationProcessor()