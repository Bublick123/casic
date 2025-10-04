from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime
import random
import httpx
from typing import List

from .database import get_db, BlackjackGame, BlackjackGameStatus
from .dependencies import get_current_user_id

router = APIRouter(prefix="/blackjack", tags=["blackjack"])

# Колода карт
DECK = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'] * 4

# Схемы Pydantic
from pydantic import BaseModel

class BlackjackStartRequest(BaseModel):
    bet_amount: float

class BlackjackActionRequest(BaseModel):
    action: str  # "hit" или "stand"

class BlackjackGameResponse(BaseModel):
    id: int
    user_id: int
    bet_amount: float
    status: str
    player_cards: List[str]
    player_score: int
    dealer_cards: List[str]
    dealer_score: int
    win_amount: float
    is_winner: bool
    is_push: bool
    created_at: datetime

def calculate_score(cards: List[str]) -> int:
    """Рассчитывает счет руки"""
    score = 0
    aces = 0
    
    for card in cards:
        if card in ['J', 'Q', 'K']:
            score += 10
        elif card == 'A':
            aces += 1
            score += 11
        else:
            score += int(card)
    
    # Обрабатываем тузы
    while score > 21 and aces > 0:
        score -= 10
        aces -= 1
    
    return score

def deal_card(used_cards: List[str]) -> str:
    """Раздает одну карту"""
    available_cards = [card for card in DECK if card not in used_cards]
    if not available_cards:
        # Если карты закончились, перемешиваем виртуально
        return random.choice(DECK)
    return random.choice(available_cards)

@router.post("/start", response_model=BlackjackGameResponse)
async def start_blackjack(
    start_data: BlackjackStartRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    authorization: str = Header(..., alias="Authorization")
):
    """Начинает новую игру в блэкджек"""
    
    # 1. Проверяем ставку
    if start_data.bet_amount <= 0:
        raise HTTPException(status_code=400, detail="Bet amount must be positive")
    
    # 2. Снимаем деньги через Wallet Service
    async with httpx.AsyncClient() as client:
        try:
            wallet_response = await client.post(
                "http://wallet-service:8000/graphql",
                json={
                    "query": f"""
                    mutation {{
                        createTransaction(type: "bet", amount: {start_data.bet_amount}) {{
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
    
    # 3. Раздаем начальные карты
    used_cards = []
    
    # Игрок: 2 карты
    player_cards = [deal_card(used_cards), deal_card(used_cards)]
    player_score = calculate_score(player_cards)
    
    # Дилер: 1 карта открыта, 1 закрыта
    dealer_cards = [deal_card(used_cards), "?"]  # Вторая карта скрыта
    dealer_score = calculate_score([dealer_cards[0]])  # Только первая карта видна
    
    # 4. Создаем игру в БД
    game = BlackjackGame(
        user_id=user_id,
        bet_amount=start_data.bet_amount,
        status=BlackjackGameStatus.PLAYER_TURN,
        player_cards=player_cards,
        player_score=player_score,
        dealer_cards=dealer_cards,
        dealer_score=dealer_score
    )
    
    db.add(game)
    db.commit()
    db.refresh(game)
 
    return BlackjackGameResponse(
        id=game.id, # type: ignore
        user_id=game.user_id,# pyright: ignore[reportArgumentType]
        bet_amount=game.bet_amount,# pyright: ignore[reportArgumentType]
        status=game.status.value,
        player_cards=game.player_cards, # pyright: ignore[reportArgumentType]
        player_score=game.player_score,# pyright: ignore[reportArgumentType]
        dealer_cards=game.dealer_cards,# pyright: ignore[reportArgumentType]
        dealer_score=game.dealer_score,# pyright: ignore[reportArgumentType]
        win_amount=game.win_amount,# pyright: ignore[reportArgumentType]
        is_winner=game.is_winner,# pyright: ignore[reportArgumentType]
        is_push=game.is_push,# pyright: ignore[reportArgumentType]
        created_at=game.created_at# pyright: ignore[reportArgumentType]
    )

@router.post("/{game_id}/action", response_model=BlackjackGameResponse)
async def player_action(
    game_id: int,
    action_data: BlackjackActionRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    authorization: str = Header(..., alias="Authorization")
):
    """Действие игрока (hit/stand)"""
    
    game = db.query(BlackjackGame).filter(
        BlackjackGame.id == game_id,
        BlackjackGame.user_id == user_id
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game.status != BlackjackGameStatus.PLAYER_TURN:# type: ignore
        raise HTTPException(status_code=400, detail="Not your turn")
    
    if action_data.action not in ["hit", "stand"]:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'hit' or 'stand'")
    
    # Восстанавливаем использованные карты
    used_cards = game.player_cards + [card for card in game.dealer_cards if card != "?"]# type: ignore
    
    if action_data.action == "hit":
        # Игрок берет карту
        new_card = deal_card(used_cards)# type: ignore
        game.player_cards.append(new_card)
        game.player_score = calculate_score(game.player_cards)# type: ignore
        
        # Проверяем перебор
        if game.player_score > 21:# type: ignore
            game.status = BlackjackGameStatus.FINISHED# type: ignore
            game.is_winner = False# type: ignore
            game.win_amount = 0.0# type: ignore
            
    else:  # stand
        # Ход дилера
        game.status = BlackjackGameStatus.DEALER_TURN# type: ignore
        await dealer_turn(game, used_cards, authorization)# type: ignore
    
    db.commit()
    db.refresh(game)
    
    return BlackjackGameResponse(
        id=game.id,# type: ignore
        user_id=game.user_id,# type: ignore
        bet_amount=game.bet_amount,# type: ignore
        status=game.status.value,
        player_cards=game.player_cards,# type: ignore
        player_score=game.player_score,# type: ignore
        dealer_cards=game.dealer_cards,# type: ignore
        dealer_score=game.dealer_score,# type: ignore
        win_amount=game.win_amount,# type: ignore
        is_winner=game.is_winner,# type: ignore
        is_push=game.is_push,# type: ignore
        created_at=game.created_at# type: ignore
    )

async def dealer_turn(game: BlackjackGame, used_cards: List[str], authorization: str):
    """Логика хода дилера"""
    # Открываем вторую карту дилера
    if "?" in game.dealer_cards:
        game.dealer_cards[1] = deal_card(used_cards)# type: ignore
        game.dealer_score = calculate_score(game.dealer_cards)# type: ignore
    
    # Дилер берет карты пока счет < 17
    while game.dealer_score < 17:# type: ignore
        new_card = deal_card(used_cards)
        game.dealer_cards.append(new_card)
        game.dealer_score = calculate_score(game.dealer_cards)# type: ignore
    
    # Определяем победителя
    game.status = BlackjackGameStatus.FINISHED# type: ignore
    await determine_winner(game, authorization)  # ← передаем authorization

async def determine_winner(game: BlackjackGame, authorization: str = None):# type: ignore
    """Определяет победителя и выплачивает выигрыш"""
    player_score = game.player_score
    dealer_score = game.dealer_score
    
    # Проверяем условия
    if player_score > 21:# type: ignore
        # Игрок перебрал
        game.is_winner = False# type: ignore
        game.win_amount = 0.0# type: ignore
    elif dealer_score > 21:# type: ignore
        # Дилер перебрал
        game.is_winner = True
        game.win_amount = game.bet_amount * 2  # Выигрыш 1:1
    elif player_score > dealer_score:
        # Игрок выиграл
        game.is_winner = True
        game.win_amount = game.bet_amount * 2
    elif player_score == dealer_score:
        # Ничья
        game.is_push = True
        game.win_amount = game.bet_amount  # Возврат ставки
    else:
        # Дилер выиграл
        game.is_winner = False
        game.win_amount = 0.0
    
    # Выплачиваем выигрыш если есть
    if game.win_amount > game.bet_amount:  # Если реальный выигрыш (не возврат)
        payout_amount = game.win_amount - game.bet_amount
        
        # Выплачиваем через Wallet Service
        async with httpx.AsyncClient() as client:
        try:
            wallet_response = await client.post(
                "http://wallet-service:8000/graphql",
                json={
                    "query": f"""
                    mutation {{
                        createTransaction(type: "win", amount: {payout_amount}) {{
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
            print(f"Payout successful: {payout_amount}$")
        except Exception as e:
            print(f"Error processing payout: {str(e)}")

    # 2. ПОТОМ отправляем уведомление (ОТДЕЛЬНЫЙ БЛОК!)
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://notification-service:8005/notifications/trigger/win",
                json={
                    "user_id": game.user_id,
                    "amount": payout_amount,  # используем уже вычисленную переменную
                    "game_type": "blackjack"
                },
                timeout=2.0
            )
            print(f"Win notification sent for user {game.user_id}")
    except Exception as e:
        print(f"Notification service error: {str(e)}")
        
@router.get("/{game_id}", response_model=BlackjackGameResponse)
async def get_blackjack_game(
    game_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """Получает информацию об игре в блэкджек"""
    game = db.query(BlackjackGame).filter(
        BlackjackGame.id == game_id,
        BlackjackGame.user_id == user_id
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return BlackjackGameResponse(
        id=game.id,
        user_id=game.user_id,
        bet_amount=game.bet_amount,
        status=game.status.value,
        player_cards=game.player_cards,
        player_score=game.player_score,
        dealer_cards=game.dealer_cards,
        dealer_score=game.dealer_score,
        win_amount=game.win_amount,
        is_winner=game.is_winner,
        is_push=game.is_push,
        created_at=game.created_at
    )

@router.get("/test")
async def blackjack_test():
    return {"message": "Blackjack is working!"}