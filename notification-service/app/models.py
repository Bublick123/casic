from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, Text
from .database import Base
from datetime import datetime

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    type = Column(String)  # email, websocket, push
    title = Column(String)
    message = Column(Text)
    status = Column(String)  # pending, sent, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    
class EmailTemplate(Base):
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)  # welcome, win_notification, deposit_confirmation
    subject = Column(String)
    template_body = Column(Text)
    is_active = Column(Boolean, default=True)
    
class WebSocketConnection(Base):
    __tablename__ = "websocket_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    connection_id = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)