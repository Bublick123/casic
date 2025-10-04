from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import logging

from . import schemas
from ..database import get_db
from ..models import Notification
from ..websocket.manager import manager
from ..queues.processor import notification_processor
from fastapi import Response
import json
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/notifications", tags=["notifications"])
import logging
logger = logging.getLogger(__name__)

# Тестовый endpoint для диагностики
@router.post("/send-debug")
async def send_debug(notification_data: schemas.NotificationCreate):
    """Диагностический endpoint"""
    from fastapi import Response
    import json
    
    try:
        logger.info(f"🔧 Pydantic data: {notification_data.dict()}")
        
        response_data = {
            "success": True,
            "received_data": notification_data.dict(),
            "message": "Pydantic works!"
        }
        
        return Response(
            content=json.dumps(response_data),
            media_type="application/json",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"❌ Pydantic error: {str(e)}")
        
        response_data = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
        
        return Response(
            content=json.dumps(response_data), 
            media_type="application/json",
            status_code=200
        )

from fastapi import Request
import json

@router.post("/send")
async def send_notification(request: dict = None):
    """Версия 3: Полная функциональность"""
    from fastapi import Response
    import json
    from app.database import SessionLocal
    
    try:
        print(f"📨 V3 Request: {request}")
        
        if request is None:
            return Response(
                content=json.dumps({"success": True, "message": "V3: No request"}),
                media_type="application/json",
                status_code=200
            )
        
        user_id = request.get("user_id")
        if not user_id:
            return Response(
                content=json.dumps({"success": False, "error": "Требуется user_id"}),
                media_type="application/json",
                status_code=200
            )
        
        notification_type = request.get("type", "email")
        
        # БД + Очередь
        db = SessionLocal()
        try:
            # Создаем в БД
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                title=request.get("title", "V3 Notification"),
                message=request.get("message", ""),
                status="queued"
            )
            
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # Отправляем в очередь
            await notification_processor.add_notification(request)
            
            print(f"✅ V3: Полная функциональность - ID: {notification.id}")
            
            response_data = {
                "success": True,
                "data": {
                    "id": notification.id,
                    "user_id": notification.user_id,
                    "type": notification.type,
                    "title": notification.title,
                    "status": notification.status
                },
                "message": "V3: Полная функциональность работает"
            }
            
            return Response(
                content=json.dumps(response_data),
                media_type="application/json",
                status_code=200
            )
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ V3 Error: {str(e)}")
        return Response(
            content=json.dumps({"success": False, "error": str(e)}),
            media_type="application/json",
            status_code=200
        )
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint для real-time уведомлений"""
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Ждем сообщения от клиента (можно использовать для ping/pong)
            data = await websocket.receive_text()
            logger.info(f"WebSocket message from user {user_id}: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@router.get("/user/{user_id}")
async def get_user_notifications(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Получение уведомлений пользователя"""
    try:
        notifications = db.query(Notification).filter(
            Notification.user_id == user_id
        ).order_by(Notification.created_at.desc()).limit(50).all()
        
        # ВОЗВРАЩАЕМ ОБЪЕКТ, а не массив!
        return {
            "success": True,
            "data": [
                {
                    "id": n.id,
                    "user_id": n.user_id,
                    "type": n.type,
                    "title": n.title,
                    "message": n.message,
                    "status": n.status,
                    "created_at": n.created_at,
                    "sent_at": n.sent_at
                }
                for n in notifications
            ],
            "count": len(notifications)
        }
        
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "count": 0
        }
@router.post("/trigger/win")
async def trigger_win_notification(win_data: dict, db: Session = Depends(get_db)):
    """Триггер уведомления о выигрыше (вызывается из game services)"""
    try:
        notification_data = {
            "user_id": win_data["user_id"],
            "type": "email",  # И websocket тоже
            "title": "🎉 Поздравляем с выигрышем!",
            "message": f"Вы выиграли ${win_data['amount']} в {win_data['game_type']}",
            "template": "win_notification",
            "context": {
                "amount": win_data["amount"],
                "game_type": win_data["game_type"],
                "date": win_data.get("date", "сегодня")
            }
        }
        
        # Email уведомление
        await notification_processor.add_notification(notification_data)
        
        # WebSocket уведомление
        ws_notification = notification_data.copy()
        ws_notification["type"] = "websocket"
        ws_notification["data"] = {
            "game_type": win_data["game_type"],
            "amount": win_data["amount"],
            "notification_type": "win"
        }
        await notification_processor.add_notification(ws_notification)
        
        return {"status": "notifications_queued"}
        
    except Exception as e:
        logger.error(f"Error triggering win notification: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send win notification")

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "notifications"}