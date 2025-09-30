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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()