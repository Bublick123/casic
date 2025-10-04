from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime
import random
import httpx

from .database import get_db, SlotGame, SlotSymbol
from .dependencies import get_current_user_id

router = APIRouter(prefix="/slots", tags=["slots"])

# Логика выплат для 3 барабанов
PAYOUT_RULES = {
    (SlotSymbol.SEVEN, SlotSymbol.SEVEN, SlotSymbol.SEVEN): 50,    # 3 семерки
    (SlotSymbol.BELL, SlotSymbol.BELL, SlotSymbol.BELL): 15,       # 3 колокола
    (SlotSymbol.PLUM, SlotSymbol.PLUM, SlotSymbol.PLUM): 10,       # 3 сливы
    (SlotSymbol.ORANGE, SlotSymbol.ORANGE, SlotSymbol.ORANGE): 5,  # 3 апельсина
    (SlotSymbol.LEMON, SlotSymbol.LEMON, SlotSymbol.LEMON): 3,     # 3 лимона
    (SlotSymbol.CHERRY, SlotSymbol.CHERRY, SlotSymbol.CHERRY): 2,  # 3 вишни
}

# Схемы Pydantic
from pydantic import BaseModel

class SlotSpinRequest(BaseModel):
    bet_amount: float

class SlotSpinResponse(BaseModel):
    id: int
    user_id: int
    bet_amount: float
    reel1: str
    reel2: str  
    reel3: str
    win_amount: float
    payout_multiplier: float
    is_winner: bool
    created_at: datetime

@router.post("/spin", response_model=SlotSpinResponse)
async def spin_slots(
    spin_data: SlotSpinRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    authorization: str = Header(..., alias="Authorization")
):
    """Крутим слоты и определяем выигрыш"""
    
    # 1. Проверяем ставку
    if spin_data.bet_amount <= 0:
        raise HTTPException(status_code=400, detail="Bet amount must be positive")
    
    # 2. Снимаем деньги через Wallet Service
    async with httpx.AsyncClient() as client:
        try:
            wallet_response = await client.post(
                "http://wallet-service:8000/graphql",
                json={
                    "query": f"""
                    mutation {{
                        createTransaction(type: "bet", amount: {spin_data.bet_amount}) {{
                            ... on TransactionSuccess {{
                                transaction {{ id amount }}
                            }}
                            ... on TransactionError {{
                                message
                            }}
                        }}
                    }}
                    """
                },
                headers={"Authorization": authorization}
            )
            
            wallet_data = wallet_response.json()
            if "errors" in wallet_data:
                error_msg = wallet_data["errors"][0]["message"]
                raise HTTPException(status_code=400, detail=f"Bet failed: {error_msg}")
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Wallet service error: {str(e)}")

    # 3. Генерируем случайные символы
    symbols = list(SlotSymbol)
    reel1 = random.choice(symbols)
    reel2 = random.choice(symbols)  
    reel3 = random.choice(symbols)
    
    # 4. Определяем выигрыш
    combination = (reel1, reel2, reel3)
    payout_multiplier = PAYOUT_RULES.get(combination, 0.0)
    win_amount = spin_data.bet_amount * payout_multiplier
    is_winner = win_amount > 0
    
    # 5. Если выиграли - зачисляем выигрыш
    if is_winner:
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    "http://wallet-service:8000/graphql",
                    json={
                        "query": f"""
                        mutation {{
                            createTransaction(type: "win", amount: {win_amount}) {{
                                ... on TransactionSuccess {{
                                    transaction {{ id amount }}
                                }}
                                ... on TransactionError {{
                                    message
                                }}
                            }}
                        }}
                        """
                    },
                    headers={"Authorization": authorization}
                )
            except Exception as e:
                print(f"Error processing win payout: {str(e)}")
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://notification-service:8005/notifications/trigger/win",
                json={
                    "user_id": user_id,  
                    "amount": win_amount,  
                    "game_type": "slots"   
                },
                timeout=2.0
             )
            print(f"Win notification sent for user {user_id}")
    except Exception as e:
         print(f"Notification service error: {str(e)}")   
    # 6. Сохраняем игру в БД
    slot_game = SlotGame(
        user_id=user_id,
        bet_amount=spin_data.bet_amount,
        reel1=reel1,
        reel2=reel2,
        reel3=reel3,
        win_amount=win_amount,
        payout_multiplier=payout_multiplier,
        is_winner=is_winner
    )
    
    db.add(slot_game)
    db.commit()
    db.refresh(slot_game)

    # 7. ОТПРАВЛЯЕМ СОБЫТИЯ В ANALYTICS (ПОСЛЕ СОХРАНЕНИЯ В БД!)
    try:
        async with httpx.AsyncClient() as client:
            # Трекаем ставку
            await client.post(
                "http://analytics-service:8004/analytics/events/game", 
                json={
                    "type": "bet",
                    "game_type": "slots",
                    "user_id": user_id, 
                    "game_id": slot_game.id,  # Теперь slot_game определена!
                    "amount": spin_data.bet_amount
                },
                timeout=2.0
            )
            
            # Если выиграли - трекаем выигрыш
            if is_winner:
                await client.post(
                    "http://analytics-service:8004/analytics/events/game",
                    json={
                        "type": "win",
                        "game_type": "slots",
                        "user_id": user_id,
                        "game_id": slot_game.id, 
                        "amount": win_amount
                    },
                    timeout=2.0
                )
    except Exception as e:
        print(f"Analytics tracking failed: {str(e)}")
    
    # 8. Возвращаем результат
    return SlotSpinResponse(
        id=slot_game.id,
        user_id=slot_game.user_id,
        bet_amount=slot_game.bet_amount,
        reel1=slot_game.reel1.value,
        reel2=slot_game.reel2.value,
        reel3=slot_game.reel3.value,
        win_amount=slot_game.win_amount,
        payout_multiplier=slot_game.payout_multiplier,
        is_winner=slot_game.is_winner,
        created_at=slot_game.created_at
    )
@router.get("/history")
async def get_slots_history(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Получаем историю игр в слотах для текущего пользователя"""
    games = db.query(SlotGame).filter(SlotGame.user_id == user_id).order_by(SlotGame.created_at.desc()).limit(10).all()
    
    return {
        "games": [
            {
                "id": game.id,
                "bet_amount": game.bet_amount,
                "reels": [game.reel1.value, game.reel2.value, game.reel3.value],
                "win_amount": game.win_amount,
                "is_winner": game.is_winner,
                "created_at": game.created_at.isoformat()
            }
            for game in games
        ]
    }

@router.get("/test")
async def slots_test():
    return {"message": "Slots are working!"}