from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import random
import httpx

from .database import get_db
from .dependencies import get_current_user_id
from .game_manager import GameManager

# ===== СХЕМЫ PYDANTIC =====
from pydantic import BaseModel

class RouletteBetPlace(BaseModel):
    bet_type: str  # ПРОСТАЯ СТРОКА!
    numbers: List[int]
    amount: float

class RouletteBetResponse(BaseModel):
    id: int
    game_id: int
    bet_type: str  # ПРОСТАЯ СТРОКА!
    numbers: List[int]
    amount: float
    payout_multiplier: float
    created_at: datetime
    is_winner: Optional[bool] = None
    payout_amount: Optional[float] = None

class RouletteGameResponse(BaseModel):
    id: int
    status: str  # ПРОСТАЯ СТРОКА!
    winning_number: Optional[int] = None
    winning_color: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    current_bets: List[RouletteBetResponse] = []

# ===== РОУТЕР =====
router = APIRouter(prefix="/roulette", tags=["roulette"])

# Менеджер игр
game_manager = GameManager()
WALLET_SERVICE_URL = "http://wallet-service:8000"

@router.post("/games", response_model=RouletteGameResponse)
async def create_game(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Создает новую игру в рулетку"""
    from .database import RouletteGame
    
    game = RouletteGame()
    db.add(game)
    db.commit()
    db.refresh(game)
    
    game_manager.add_game(game.id)
    
    # ВАЖНО: конвертируем Enum в строку!
    return RouletteGameResponse(
        id=game.id,
        status=game.status.value if game.status else "waiting",  # ← .value ДЛЯ СТРОКИ!
        winning_number=game.winning_number,
        winning_color=game.winning_color,
        created_at=game.created_at,
        started_at=game.started_at,
        finished_at=game.finished_at,
        current_bets=[]
    )

@router.get("/games/{game_id}", response_model=RouletteGameResponse)
async def get_game(
    game_id: int,
    db: Session = Depends(get_db)
):
    """Получает информацию об игре"""
    from .database import RouletteGame, RouletteBet
    
    game = db.query(RouletteGame).filter(RouletteGame.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    bets = db.query(RouletteBet).filter(RouletteBet.game_id == game_id).all()
    
    # Конвертируем ставки
    bet_responses = []
    for bet in bets:
        bet_responses.append(RouletteBetResponse(
            id=bet.id,
            game_id=bet.game_id,
            bet_type=bet.bet_type.value if bet.bet_type else "",  # ← .value ДЛЯ СТРОКИ!
            numbers=bet.numbers or [],
            amount=bet.amount or 0.0,
            payout_multiplier=bet.payout_multiplier or 1.0,
            created_at=bet.created_at,
            is_winner=bet.is_winner,
            payout_amount=bet.payout_amount
        ))
    
    return RouletteGameResponse(
        id=game.id,
        status=game.status.value if game.status else "waiting",  # ← .value ДЛЯ СТРОКИ!
        winning_number=game.winning_number,
        winning_color=game.winning_color,
        created_at=game.created_at,
        started_at=game.started_at,
        finished_at=game.finished_at,
        current_bets=bet_responses
    )

@router.post("/games/{game_id}/bet", response_model=RouletteBetResponse)
async def place_bet(
    game_id: int,
    bet_data: RouletteBetPlace,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Размещает ставку в игре"""
    from .database import RouletteGame, RouletteBet, RouletteBetType
    
    game = db.query(RouletteGame).filter(RouletteGame.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Простая валидация
    if bet_data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Конвертируем строку в Enum для сохранения в БД
    try:
        bet_type_enum = RouletteBetType(bet_data.bet_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bet type")
    
    # Создаем ставку в БД
    bet = RouletteBet(
        game_id=game_id,
        user_id=user_id,
        bet_type=bet_type_enum,
        numbers=bet_data.numbers,
        amount=bet_data.amount,
        payout_multiplier=2.0  # Простой множитель для теста
    )
    
    db.add(bet)
    db.commit()
    db.refresh(bet)
    
    # Конвертируем обратно в строку для ответа
    return RouletteBetResponse(
        id=bet.id,
        game_id=bet.game_id,
        bet_type=bet.bet_type.value,  # ← .value ДЛЯ СТРОКИ!
        numbers=bet.numbers or [],
        amount=bet.amount or 0.0,
        payout_multiplier=bet.payout_multiplier or 1.0,
        created_at=bet.created_at,
        is_winner=bet.is_winner,
        payout_amount=bet.payout_amount
    )

@router.get("/games")
async def get_active_games_fixed(db: Session = Depends(get_db)):
    """Получает список активных игр - исправленная версия для KrakenD"""
    from .database import RouletteGame, RouletteBet
    
    games = db.query(RouletteGame).all()
    
    game_list = []
    for game in games:
        bets = db.query(RouletteBet).filter(RouletteBet.game_id == game.id).all()
        
        bet_list = []
        for bet in bets:
            bet_list.append({
                "id": bet.id,
                "game_id": bet.game_id,
                "bet_type": bet.bet_type.value if bet.bet_type else "unknown",
                "numbers": bet.numbers or [],
                "amount": float(bet.amount) if bet.amount else 0.0,
                "payout_multiplier": float(bet.payout_multiplier) if bet.payout_multiplier else 1.0,
                "created_at": bet.created_at.isoformat() if bet.created_at else None,
                "is_winner": bet.is_winner,
                "payout_amount": float(bet.payout_amount) if bet.payout_amount else None
            })
        
        game_list.append({
            "id": game.id,
            "status": game.status.value if game.status else "waiting",
            "winning_number": game.winning_number,
            "winning_color": game.winning_color,
            "created_at": game.created_at.isoformat() if game.created_at else None,
            "started_at": game.started_at.isoformat() if game.started_at else None,
            "finished_at": game.finished_at.isoformat() if game.finished_at else None,
            "current_bets": bet_list
        })
    
    # Ключевое исправление: возвращаем объект, а не массив
    return {
        "success": True,
        "games": game_list,
        "count": len(game_list)
    }

@router.get("/test")
async def roulette_test():
    return {"message": "Roulette is working!"}