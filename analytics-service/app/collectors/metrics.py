from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

# Метрики для игр
BETS_COUNTER = Counter('bets_total', 'Total bets placed', ['game_type', 'status'])
WINS_COUNTER = Counter('wins_total', 'Total wins', ['game_type'])
BET_AMOUNT = Histogram('bet_amount', 'Bet amount distribution', ['game_type'])
WIN_AMOUNT = Histogram('win_amount', 'Win amount distribution', ['game_type'])

# Метрики для пользователей
ACTIVE_USERS = Gauge('active_users', 'Currently active users')
NEW_USERS = Counter('new_users_total', 'Total new registrations')

# Финансовые метрики
TOTAL_REVENUE = Gauge('total_revenue', 'Total casino revenue')
HOUSE_EDGE = Gauge('house_edge', 'Casino house edge percentage')

def get_metrics():
    return generate_latest()