import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

from .main import app
from . import models
from .database import get_db
from .models import Base  # Импортируем Base из models!

# Тестовая БД в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Фикстура для БД с созданием 123
@pytest.fixture(scope="function")
def db_session():
    # Создаем таблицы ПЕРЕД каждым тестом
    Base.metadata.create_all(bind=engine)
    
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    # Чистим после каждого теста
    session.close()
    transaction.rollback()
    connection.close()
    Base.metadata.drop_all(bind=engine)

# Мок для Redis
@pytest.fixture
def mock_redis():
    with patch('app.schema.redis_client') as mock:
        mock.get.return_value = None
        mock.setex.return_value = None
        yield mock

# Фикстура для клиента
@pytest.fixture
def client(db_session, mock_redis):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# Тестовые данные
TEST_USER_ID = "1"
TEST_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.dummy_token"

def test_get_balance_new_user(client, db_session, mock_redis):
    """Тест получения баланса для нового пользователя"""
    with patch('app.main.get_current_user_id', return_value=TEST_USER_ID):
        response = client.post(
            "/graphql",
            json={"query": "query { getBalance { __typename ... on Balance { balance currency } ... on TransactionError { message } } }"},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        print("Response:", data)
        assert data["data"]["getBalance"]["__typename"] == "Balance"
        assert data["data"]["getBalance"]["balance"] == 0.0
        assert data["data"]["getBalance"]["currency"] == "USD"

def test_deposit_transaction(client, db_session, mock_redis):
    """Тест успешного депозита"""
    # Сначала создаем кошелек
    wallet = models.Wallet(user_id=1, balance=0.0, currency="USD")
    db_session.add(wallet)
    db_session.commit()
    
    with patch('app.main.get_current_user_id', return_value=TEST_USER_ID):
        response = client.post(
            "/graphql",
            json={"query": 'mutation { createTransaction(type: "deposit", amount: 100.0) { __typename ... on TransactionSuccess { transaction { id amount type } } ... on TransactionError { message } } }'},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        print("Deposit response:", data)
        assert data["data"]["createTransaction"]["__typename"] == "TransactionSuccess"
        assert data["data"]["createTransaction"]["transaction"]["amount"] == 100.0
        assert data["data"]["createTransaction"]["transaction"]["type"] == "deposit"

def test_insufficient_funds(client, db_session, mock_redis):
    """Тест ошибки недостатка средств"""
    # Создаем кошелек с малым балансом
    wallet = models.Wallet(user_id=1, balance=50.0, currency="USD")
    db_session.add(wallet)
    db_session.commit()
    
    with patch('app.main.get_current_user_id', return_value=TEST_USER_ID):
        response = client.post(
            "/graphql",
            json={"query": 'mutation { createTransaction(type: "withdraw", amount: 100.0) { __typename ... on TransactionSuccess { transaction { id } } ... on TransactionError { message } } }'},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        print("Insufficient funds response:", data)
        assert data["data"]["createTransaction"]["__typename"] == "TransactionError"
        assert "Insufficient funds" in data["data"]["createTransaction"]["message"]

def test_invalid_transaction_type(client, db_session, mock_redis):
    """Тест ошибки неверного типа транзакции"""
    with patch('app.main.get_current_user_id', return_value=TEST_USER_ID):
        response = client.post(
            "/graphql",
            json={"query": 'mutation { createTransaction(type: "invalid", amount: 100.0) { __typename ... on TransactionSuccess { transaction { id } } ... on TransactionError { message } } }'},
            headers={"Authorization": f"Bearer {TEST_TOKEN}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        print("Invalid type response:", data)
        assert data["data"]["createTransaction"]["__typename"] == "TransactionError"
        assert "Invalid transaction type" in data["data"]["createTransaction"]["message"]

def test_not_authenticated(client, db_session, mock_redis):
    """Тест ошибки аутентификации"""
    with patch('app.main.get_current_user_id', return_value=None):
        response = client.post(
            "/graphql", 
            json={"query": "query { getBalance { __typename ... on Balance { balance } ... on TransactionError { message } } }"},
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        print("Not authenticated response:", data)
        assert data["data"]["getBalance"]["__typename"] == "TransactionError"
        assert "Not authenticated" in data["data"]["getBalance"]["message"]