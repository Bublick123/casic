from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class UserResponse(BaseModel):
    id: int
    login: str
    email: str
    role: str
    created_at: datetime
    last_login: Optional[datetime]

class GameStatsResponse(BaseModel):
    game_type: str
    total_bets: int
    total_wins: int
    total_revenue: float
    house_edge: float

class FinancialStatsResponse(BaseModel):
    total_deposits: float
    total_withdrawals: float
    net_revenue: float
    active_users: int