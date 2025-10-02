from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class GameStatResponse(BaseModel):
    game_type: str
    total_bets: int
    total_wins: int
    total_revenue: float
    house_edge: float

class UserStatResponse(BaseModel):
    user_id: int
    total_bets: int
    total_wins: int
    win_rate: float
    favorite_game: str

class RevenueResponse(BaseModel):
    date: str
    total_bets: float
    total_wins: float
    net_revenue: float
    player_count: int