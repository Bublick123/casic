import strawberry
from datetime import datetime
from sqlalchemy.orm import Session

from . import models
from .database import get_db  
from .redis_client import redis_client
from .models import TransactionType, TransactionStatus
from fastapi import Depends
import strawberry
from strawberry.types import Info
import strawberry
from typing import Union, List, Optional










@strawberry.type
class TransactionError:
    message: str


@strawberry.type
class TransactionSuccess:
    transaction: 'Transaction'




TransactionResult = strawberry.union(
    name="TransactionResult",
    types=(TransactionSuccess, TransactionError),
)









@strawberry.type
class Wallet:
    id: strawberry.ID                                                       
    user_id: strawberry.ID
    balance: float
    currency: str

@strawberry.type
class Transaction:
    id: strawberry.ID
    wallet_id: strawberry.ID
    type: str
    amount: float
    status: str
    created_at: str



class InsufficientFundsError:
    def __init__(self, message):
        self.message = message

@strawberry.type
class Balance:
    balance: float
    currency: str
BalanceResult = Union[Balance, TransactionError]


@strawberry.type
class Query:

    @strawberry.field
    def get_balance(self, info) -> BalanceResult:
        db: Session = info.context["db"]
        user_id = info.context["user_id"]
        
        if not user_id:
            return TransactionError(message="Not authenticated")
        
        try:
            cache_key = f"wallet:{user_id}"
            cached_balance = redis_client.get(cache_key)

            if cached_balance:
                return Balance(balance=float(cached_balance), currency="USD")# type: ignore

            wallet = db.query(models.Wallet).filter(models.Wallet.user_id == int(user_id)).first()

            if not wallet:
                wallet = models.Wallet(user_id=int(user_id), balance=0.0, currency="USD")
                db.add(wallet)
                db.commit()
                db.refresh(wallet)

            redis_client.setex(cache_key, 300, wallet.balance) # type: ignore
            return Balance(balance=wallet.balance, currency=wallet.currency)# type: ignore
            
        except Exception as e:
            return TransactionError(message=f"Internal server error: {str(e)}")
        
    @strawberry.field
    def get_transactions(self, info) -> List[Transaction]:
        db: Session = info.context["db"]
        user_id = info.context["user_id"] 
        wallet = db.query(models.Wallet).filter(models.Wallet.user_id == int(user_id)).first()
        if not wallet:
            return []

        transactions = db.query(models.Transaction).filter(models.Transaction.wallet_id == wallet.id).all()
        return [
            Transaction(
                id=strawberry.ID(str(tx.id)),
                wallet_id=strawberry.ID(str(tx.wallet_id)),
                type=tx.type.value,
                amount=tx.amount,# type: ignore
                status=tx.status.value,
                created_at=tx.created_at.isoformat()
            )
            for tx in transactions
        ]






@strawberry.type
class Mutation: 

    @strawberry.mutation
    def create_transaction(self, info, type: str, amount: float) -> TransactionResult:# type: ignore
        db: Session = info.context["db"]
        user_id = info.context["user_id"]
        
        if not user_id:
            return TransactionError(message="Not authenticated")
        
        if amount <= 0:
            return TransactionError(message="Amount must be positive")
        
        try:
            wallet = db.query(models.Wallet).filter(models.Wallet.user_id == int(user_id)).first()
            
            if not wallet:
                wallet = models.Wallet(user_id=int(user_id), balance=0.0, currency="USD")
                db.add(wallet)
                db.commit()
                db.refresh(wallet)

            type_lower = type.lower()
            try:
                tx_type = models.TransactionType(type_lower)
            except ValueError:
                valid_types = [t.value for t in models.TransactionType]
                return TransactionError(
                    message=f"Invalid transaction type. Valid types: {', '.join(valid_types)}"
                )

            tx_status = models.TransactionStatus.PENDING
            
            if tx_type == models.TransactionType.DEPOSIT:
                wallet.balance += amount# type: ignore
                tx_status = models.TransactionStatus.COMPLETED
                
            elif tx_type == models.TransactionType.WITHDRAW:
                if wallet.balance >= amount:# type: ignore
                    wallet.balance -= amount# type: ignore
                    tx_status = models.TransactionStatus.COMPLETED
                else:
                    return TransactionError(message="Insufficient funds")
                    
            elif tx_type == models.TransactionType.BET:
                if wallet.balance >= amount:# type: ignore
                    wallet.balance -= amount# type: ignore
                    tx_status = models.TransactionStatus.COMPLETED
                else:
                    return TransactionError(message="Insufficient funds for bet")
                    
            elif tx_type == models.TransactionType.WIN:
                wallet.balance += amount# type: ignore
                tx_status = models.TransactionStatus.COMPLETED

            transaction = models.Transaction(
                wallet_id=wallet.id,
                type=tx_type,
                amount=amount,
                status=tx_status,
                created_at=datetime.utcnow()
            )

            db.add(transaction)
            db.commit()
            db.refresh(transaction)

            cache_key = f"wallet:{user_id}"
            redis_client.setex(cache_key, 300, wallet.balance)# type: ignore

            return TransactionSuccess(
                transaction=Transaction(
                    id=strawberry.ID(str(transaction.id)),
                    wallet_id=strawberry.ID(str(transaction.wallet_id)),
                    type=transaction.type.value,
                    amount=transaction.amount,# type: ignore
                    status=transaction.status.value,
                    created_at=transaction.created_at.isoformat()
                )
            )
            
        except Exception as e:
            db.rollback()
            return TransactionError(message=f"Transaction failed: {str(e)}")

    @strawberry.mutation
    def process_bet_win(
        self,
        info,
        bet_amount: float,
        win_amount: Optional[float] = None
    ) -> TransactionResult:# type: ignore
        """
        Комбинированная операция: сначала ставка, затем (опционально) выигрыш.
        Полезно для игровых сервисов.
        """
        db: Session = info.context["db"]
        user_id = info.context["user_id"]
        
        if bet_amount <= 0:
            return TransactionError(message="Bet amount must be positive")
        
        if win_amount is not None and win_amount < 0:
            return TransactionError(message="Win amount cannot be negative")
        
        # Находим кошелек
        wallet = db.query(models.Wallet).filter(
            models.Wallet.user_id == int(user_id)
        ).first()
        
        if not wallet:
            return TransactionError(message="Wallet not found")
        
        # Проверяем достаточно ли средств для ставки
        if wallet.balance < bet_amount:# type: ignore
            return TransactionError(message="Insufficient funds for bet")
        
        # Создаем транзакцию ставки
        bet_transaction = models.Transaction(
            wallet_id=wallet.id,
            type=models.TransactionType.BET,
            amount=bet_amount,
            status=models.TransactionStatus.COMPLETED,
            created_at=datetime.utcnow()
        )
        
        wallet.balance -= bet_amount# type: ignore
        
        # Если есть выигрыш, создаем транзакцию выигрыша
        win_transaction = None
        if win_amount and win_amount > 0:
            win_transaction = models.Transaction(
                wallet_id=wallet.id,
                type=models.TransactionType.WIN,
                amount=win_amount,
                status=models.TransactionStatus.COMPLETED,
                created_at=datetime.utcnow()
            )
            wallet.balance += win_amount# type: ignore
            db.add(win_transaction)
        
        db.add(bet_transaction)
        db.commit()
        
        if win_transaction:
            db.refresh(win_transaction)
            result_transaction = win_transaction
        else:
            db.refresh(bet_transaction)
            result_transaction = bet_transaction
        
        # Обновляем кэш
        cache_key = f"wallet:{user_id}"
        redis_client.setex(cache_key, 300, wallet.balance)# type: ignore
        
        return TransactionSuccess(
            transaction=Transaction(
                id=strawberry.ID(str(result_transaction.id)),
                wallet_id=strawberry.ID(str(result_transaction.wallet_id)),
                type=result_transaction.type.value,
                amount=result_transaction.amount,# type: ignore
                status=result_transaction.status.value,
                created_at=result_transaction.created_at.isoformat()
            )
        )

# Схема остается без изменений
schema = strawberry.Schema(query=Query, mutation=Mutation)