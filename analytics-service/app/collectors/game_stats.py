from sqlalchemy.orm import Session
from prometheus_client import Counter, Histogram
from ..models import GameStat
import logging

logger = logging.getLogger(__name__)

class GameStatsCollector:
    def __init__(self):
        self.bets_counter = Counter('game_bets_total', 'Total bets by game type', ['game_type'])
        self.wins_counter = Counter('game_wins_total', 'Total wins by game type', ['game_type'])
        self.bet_amount_histogram = Histogram('game_bet_amount', 'Bet amount distribution', ['game_type'])
    
    async def track_bet(self, db: Session, game_type: str, user_id: int, game_id: int, bet_amount: float):
        """Трекинг ставки"""
        try:
            # Сохраняем в БД
            game_stat = GameStat(
                game_type=game_type,
                game_id=game_id,
                user_id=user_id,
                bet_amount=bet_amount,
                win_amount=0.0,
                is_winner=False
            )
            db.add(game_stat)
            db.commit()
            
            # Обновляем Prometheus метрики
            self.bets_counter.labels(game_type=game_type).inc()
            self.bet_amount_histogram.labels(game_type=game_type).observe(bet_amount)
            
            logger.info(f"Tracked bet: {game_type}, user_id={user_id}, amount={bet_amount}")
            
        except Exception as e:
            logger.error(f"Error tracking bet: {str(e)}")
            db.rollback()
    
    async def track_win(self, db: Session, game_type: str, user_id: int, game_id: int, win_amount: float):
        """Трекинг выигрыша"""
        try:
            # Находим последнюю ставку пользователя в этой игре
            game_stat = db.query(GameStat).filter(
                GameStat.game_type == game_type,
                GameStat.user_id == user_id,
                GameStat.game_id == game_id,
                GameStat.is_winner == False
            ).order_by(GameStat.created_at.desc()).first()
            
            if game_stat:
                game_stat.win_amount = win_amount
                game_stat.is_winner = True
                db.commit()
                
                # Обновляем Prometheus метрики
                self.wins_counter.labels(game_type=game_type).inc()
                self.bet_amount_histogram.labels(game_type=game_type).observe(win_amount)
                
                logger.info(f"Tracked win: {game_type}, user_id={user_id}, amount={win_amount}")
                
        except Exception as e:
            logger.error(f"Error tracking win: {str(e)}")
            db.rollback()

# Глобальный инстанс коллектора
game_stats = GameStatsCollector()