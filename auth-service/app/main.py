from fastapi import FastAPI, Depends, HTTPException, status, Request, Body, Response
from sqlalchemy.orm import Session
from . import models, schemas, utils
from .database import engine, Base, get_db 
from .dependencies import get_current_user, oauth2_scheme, get_admin_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from datetime import datetime, timedelta
from typing import List
from fastapi.responses import JSONResponse

# Сначала создаем таблицы
models.Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()
SECRET_KEY = "your-super-secret-key-here"

# 🔥 ПРОСТОЙ STARTUP EVENT (работает)
@app.on_event("startup")
async def startup_event():
    """Создаем админа при запуске если его нет"""
    print("🚀 Startup event started!")
    db_generator = get_db()
    db = next(db_generator)
    try:
        print("🔍 Checking for admin user...")
        admin_user = db.query(models.User).filter(models.User.login == "admin").first()
        
        if not admin_user:
            print("👤 Admin not found, creating...")
            # Создаем админа
            hashed_password = utils.hash_password("admin123")
            admin_user = models.User(
                login="admin",
                email="admin@casino.com", 
                hashed_password=hashed_password,
                role="admin"
            )
            db.add(admin_user)
            db.commit()
            print("✅ Admin user created: admin / admin123")
        else:
            print(f"👤 Admin found: {admin_user.login}, updating role...")
            # Обновляем существующего админа
            admin_user.role = "admin"
            db.commit()
            print("✅ Existing admin user updated to admin role")
            
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
    finally:
        try:
            next(db_generator)
        except StopIteration:
            pass

# Middleware и остальной код...
@app.middleware("http")
async def swagger_auth_fix(request: Request, call_next):
    token = request.query_params.get("token")
    
    if token:
        headers = dict(request.headers)
        headers["authorization"] = f"Bearer {token}"
        
        request._headers = headers
        request.scope["headers"] = [
            (key.encode(), value.encode()) 
            for key, value in headers.items()
        ]
    
    response = await call_next(request)
    return response

security = HTTPBearer(auto_error=False)

# 🔥 ОСНОВНЫЕ ENDPOINTS
@app.post("/register", response_model=schemas.UserResponse)
async def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    password = user_data.password
    password_bytes = password.encode("utf-8")
    if not utils.validate_password_complexity(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters with uppercase, lowercase, number and special character"
        )
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=400,
            detail=f"Password too long ({len(password_bytes)} bytes). Maximum is 72 bytes."
        )

    # Проверка уникальности
    db_user = db.query(models.User).filter(
        (models.User.login == user_data.login) | 
        (models.User.email == user_data.email)
    ).first()
    
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this login or email already exists"
        )
    
    # Создание пользователя
    hashed_password = utils.hash_password(user_data.password)
    db_user = models.User(
        login=user_data.login,
        email=user_data.email,
        hashed_password=hashed_password,                                                        
        created_at=datetime.utcnow(),
        role="user"  # 🔥 По умолчанию user
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/login", response_model=schemas.Token)
async def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.login == login_data.login).first()
    
    if not user or not utils.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    user.login_count += 1         
    user.last_login = datetime.now() 
    db.commit()
    
    access_token = utils.create_access_token(data={"sub": str(user.id)})
    refresh_token = utils.create_refresh_token(data={"sub": str(user.id)})

    db_refresh_token = models.RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(db_refresh_token)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@app.get("/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.get("/protected")
async def protected_route(current_user: models.User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.login}!", "user_id": current_user.id}

# 🔥 АДМИН ENDPOINTS
@app.get("/admin/users", response_model=List[schemas.UserResponse])
async def get_all_users_admin(
    admin_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Получение всех пользователей (только для админов)"""
    users = db.query(models.User).all()
    return users

@app.patch("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_data: schemas.UserRoleUpdate,
    admin_user: models.User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):                                                          
    """Изменение роли пользователя (только для админов)"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.role = role_data.role
    db.commit()
    db.refresh(user)

    return {"message": f"User role updated to {role_data.role}"}

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "auth"}

@app.get("/__health")
async def health_check_compat():
    return {"status": "healthy", "service": "auth"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)