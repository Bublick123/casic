from sqlalchemy.orm import Session
from ..models import UserStat
from prometheus_client import Gauge, Counter
import logging
import datetime
logger = logging.getLogger(__name__)

class UserStatsCollector:
    def __init__(self):
        self.active_users_gauge = Gauge('active_users_total', 'Total active users')
        self.user_registrations = Counter('user_registrations_total', 'Total user registrations')
    
    async def update_user_stats(self, db: Session, user_id: int, bet_amount: float = 0, win_amount: float = 0):
        """Обновление статистики пользователя"""
        try:
            user_stat = db.query(UserStat).filter(UserStat.user_id == user_id).first()
            
            if not user_stat:
                # Создаем новую запись
                user_stat = UserStat(
                    user_id=user_id,
                    total_bets=1 if bet_amount > 0 else 0,
                    total_wins=1 if win_amount > 0 else 0,
                    total_deposits=0.0,
                    total_withdrawals=0.0,
                    current_balance=0.0
                )
                db.add(user_stat)
                self.user_registrations.inc()
            else:
                # Обновляем существующую
                if bet_amount > 0:
                    user_stat.total_bets += 1
                if win_amount > 0:
                    user_stat.total_wins += 1
                
                user_stat.last_activity = datetime.utcnow()
            
            db.commit()
            self.active_users_gauge.inc()
            
            logger.info(f"Updated user stats: user_id={user_id}, bets={user_stat.total_bets}, wins={user_stat.total_wins}")
            
        except Exception as e:
            logger.error(f"Error updating user stats: {str(e)}")
            db.rollback()
    
    async def track_deposit(self, db: Session, user_id: int, amount: float):
        """Трекинг депозита"""
        try:
            user_stat = db.query(UserStat).filter(UserStat.user_id == user_id).first()
            if user_stat:
                user_stat.total_deposits += amount
                user_stat.current_balance += amount
                db.commit()
                logger.info(f"Tracked deposit: user_id={user_id}, amount={amount}")
                
        except Exception as e:
            logger.error(f"Error tracking deposit: {str(e)}")
            db.rollback()

# Глобальный инстанс коллектора
user_stats = UserStatsCollector()