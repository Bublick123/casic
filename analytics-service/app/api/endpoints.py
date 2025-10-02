from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from sqlalchemy import func
import logging

# ПРАВИЛЬНЫЕ ИМПОРТЫ - из корневой директории app
from app.database import get_db
from app.models import GameStat, UserStat
from app.collectors.metrics import get_metrics
from app.collectors.game_stats import game_stats
from app.collectors.user_stats import user_stats
from app.api import schemas
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])
@router.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint - только для прямого доступа"""
    try:
        metrics_data = get_metrics()
        return Response(metrics_data, media_type="text/plain")
    except Exception as e:
        logger.error(f"Error generating metrics: {str(e)}")
        # Возвращаем простой текст вместо ошибки
        return Response("", media_type="text/plain")

@router.get("/games/stats")
async def get_game_stats(db: Session = Depends(get_db)):
    """Статистика по играм"""
    try:
        logger.info("Getting game stats...")
        
        # Простая агрегация
        stats = db.query(
            GameStat.game_type,
            func.count(GameStat.id).label('total_bets'),
            func.sum(GameStat.win_amount).label('total_wins'),
        ).group_by(GameStat.game_type).all()
        
        result = []
        for stat in stats:
            total_bets_amount = db.query(func.sum(GameStat.bet_amount)).filter(
                GameStat.game_type == stat.game_type
            ).scalar() or 0
            
            total_revenue = total_bets_amount - (stat.total_wins or 0)
            house_edge = (total_revenue / total_bets_amount * 100) if total_bets_amount > 0 else 0
            
            result.append({
                "game_type": stat.game_type or "unknown",
                "total_bets": stat.total_bets or 0,
                "total_wins": stat.total_wins or 0,
                "total_revenue": total_revenue,
                "house_edge": round(house_edge, 2)
            })
        
        # ВОЗВРАЩАЕМ ОБЪЕКТ, а не массив!
        return {
            "success": True,
            "data": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error getting game stats: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }

@router.get("/users/{user_id}/stats")
async def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    """Статистика по конкретному пользователю"""
    try:
        from ..models import UserStat, GameStat
        
        user_stat = db.query(UserStat).filter(UserStat.user_id == user_id).first()
        if not user_stat:
            raise HTTPException(status_code=404, detail="User stats not found")
        
        # Находим любимую игру пользователя
        favorite_game = db.query(
            GameStat.game_type,
            func.count(GameStat.id).label('game_count')
        ).filter(
            GameStat.user_id == user_id
        ).group_by(GameStat.game_type).order_by(func.count(GameStat.id).desc()).first()
        
        win_rate = (user_stat.total_wins / user_stat.total_bets * 100) if user_stat.total_bets > 0 else 0
        
        return schemas.UserStatResponse(
            user_id=user_stat.user_id,
            total_bets=user_stat.total_bets,
            total_wins=user_stat.total_wins,
            win_rate=round(win_rate, 2),
            favorite_game=favorite_game[0] if favorite_game else "none"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/events/game")
async def track_game_event(event_data: dict, db: Session = Depends(get_db)):
    """Трекинг игровых событий"""
    try:
        event_type = event_data.get("type")
        game_type = event_data.get("game_type")
        user_id = event_data.get("user_id")
        game_id = event_data.get("game_id")
        amount = event_data.get("amount", 0.0)
        
        if event_type == "bet":
            await game_stats.track_bet(db, game_type, user_id, game_id, amount)
            await user_stats.update_user_stats(db, user_id, bet_amount=amount)
        elif event_type == "win":
            await game_stats.track_win(db, game_type, user_id, game_id, amount)
            await user_stats.update_user_stats(db, user_id, win_amount=amount)
        elif event_type == "deposit":
            await user_stats.track_deposit(db, user_id, amount)
        
        return {"status": "tracked", "event": event_type}
        
    except Exception as e:
        logger.error(f"Error tracking game event: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "analytics"}