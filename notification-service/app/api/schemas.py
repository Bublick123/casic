from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class NotificationCreate(BaseModel):
    user_id: int
    type: str
    title: Optional[str] = None
    message: Optional[str] = None

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    status: str
    created_at: datetime
    sent_at: Optional[datetime]

class WebSocketMessage(BaseModel):
    type: str
    user_id: int
    data: Dict[str, Any]