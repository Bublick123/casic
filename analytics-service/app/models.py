from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean
from .database import Base
from datetime import datetime

class GameStat(Base):
    __tablename__ = "game_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    game_type = Column(String)  # roulette, slots, blackjack
    game_id = Column(Integer)
    user_id = Column(Integer)
    bet_amount = Column(Float)
    win_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_winner = Column(Boolean)

class UserStat(Base):
    __tablename__ = "user_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    total_bets = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    total_losses = Column(Integer, default=0)
    total_deposits = Column(Float, default=0.0)
    total_withdrawals = Column(Float, default=0.0)
    current_balance = Column(Float, default=0.0)
    last_activity = Column(DateTime, default=datetime.utcnow)

class DailyRevenue(Base):
    __tablename__ = "daily_revenue"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)  # YYYY-MM-DD
    total_bets = Column(Float, default=0.0)
    total_wins = Column(Float, default=0.0)
    net_revenue = Column(Float, default=0.0)  # total_bets - total_wins
    player_count = Column(Integer, default=0)