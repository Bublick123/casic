from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime
import enum

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://casino_user:casino_password@game-postgres:5432/game_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# МОДЕЛИ БД
#Рулетка
class RouletteGameStatus(enum.Enum):
    WAITING = "waiting"
    ACCEPTING_BETS = "accepting_bets"
    NO_MORE_BETS = "no_more_bets"
    SPINNING = "spinning"
    FINISHED = "finished"

class RouletteBetType(enum.Enum):
    STRAIGHT = "straight"
    SPLIT = "split"
    STREET = "street"
    CORNER = "corner"
    RED = "red"
    BLACK = "black"
    EVEN = "even"
    ODD = "odd"
    LOW = "low"
    HIGH = "high"
    DOZEN = "dozen"
    COLUMN = "column"

class RouletteGame(Base):
    __tablename__ = "roulette_games"
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    winning_number = Column(Integer, nullable=True)
    winning_color = Column(String, nullable=True)
    status = Column(SQLEnum(RouletteGameStatus), default=RouletteGameStatus.WAITING)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

class RouletteBet(Base):
    __tablename__ = "roulette_bets"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    bet_type = Column(SQLEnum(RouletteBetType))
    numbers = Column(JSON)
    amount = Column(Float)
    payout_multiplier = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_winner = Column(Boolean, nullable=True)
    payout_amount = Column(Float, nullable=True)

#Слоты
class SlotSymbol(enum.Enum):
    CHERRY = "cherry"
    LEMON = "lemon" 
    ORANGE = "orange"
    PLUM = "plum"
    BELL = "bell"
    SEVEN = "seven"

class SlotGame(Base):
    __tablename__ = "slot_games"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    bet_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    reel1 = Column(SQLEnum(SlotSymbol))  # Символ на первом барабане
    reel2 = Column(SQLEnum(SlotSymbol))  
    reel3 = Column(SQLEnum(SlotSymbol))
    win_amount = Column(Float, default=0.0)
    payout_multiplier = Column(Float, default=0.0)
    is_winner = Column(Boolean, default=False)
#blackjack


class BlackjackGameStatus(enum.Enum):
    WAITING = "waiting"
    PLAYER_TURN = "player_turn"
    DEALER_TURN = "dealer_turn"
    FINISHED = "finished"

class BlackjackGame(Base):
    __tablename__ = "blackjack_games"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    bet_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(SQLEnum(BlackjackGameStatus), default=BlackjackGameStatus.WAITING)
    
    # Карты игрока (JSON список)
    player_cards = Column(JSON)
    player_score = Column(Integer, default=0)
    
    # Карты дилера
    dealer_cards = Column(JSON) 
    dealer_score = Column(Integer, default=0)
    
    # Результат
    win_amount = Column(Float, default=0.0)
    is_winner = Column(Boolean, default=False)
    is_push = Column(Boolean, default=False)  # Ничья

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()