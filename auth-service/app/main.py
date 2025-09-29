from fastapi import FastAPI, Depends, HTTPException, status, Request, Body, Response
from sqlalchemy.orm import Session
from . import models, schemas, utils
from .database import engine, Base, get_db 
from .dependencies import get_current_user, oauth2_scheme
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.openapi.models import OAuthFlowPassword
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from datetime import datetime, timedelta
models.Base.metadata.create_all(bind=engine)
from . import dependencies
from typing import List
import base64
from fastapi.responses import JSONResponse
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)



app = FastAPI()
SECRET_KEY = "your-super-secret-key-here"


@app.middleware("http")
async def swagger_auth_fix(request: Request, call_next):
    # Проверяем есть ли token в query параметрах
    token = request.query_params.get("token")
    
    if token:
        # Создаем новый заголовок Authorization
        headers = dict(request.headers)
        headers["authorization"] = f"Bearer {token}"
        
        # Создаем новый request с обновленными headers
        request._headers = headers
        request.scope["headers"] = [
            (key.encode(), value.encode()) 
            for key, value in headers.items()
        ]
    
    response = await call_next(request)
    return response



security = HTTPBearer(auto_error=False)





@app.post("/register", response_model=schemas.UserResponse)
async def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    password = user_data.password
    password_bytes = password.encode("utf-8")
    if not utils.validate_password_complexity(user_data.password): #Валидация пароля
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters with uppercase, lowercase, number and special character"
        )
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=400,
            detail=f"Password too long ({len(password_bytes)} bytes). Maximum is 72 bytes."
        )
    
    # Можно дополнительно логировать
    print(f"Password length in bytes: {len(password_bytes)}")





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
    
    #хеш пароля
    hashed_password = utils.hash_password(user_data.password)
    

    #cоздание юзера
    db_user = models.User(
    login=user_data.login,
    email=user_data.email,
    hashed_password=hashed_password,                                                        
    created_at=datetime.utcnow()  
)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    print(f"Password received: {user_data.password}, length: {len(user_data.password)}")
    return db_user

@app.post("/login", response_model=schemas.Token)
async def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    # Находим пользователя
    user = db.query(models.User).filter(models.User.login == login_data.login).first()
    
    if not user or not utils.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
     # 
    user.login_count += 1         
    user.last_login = datetime.now() 
    db.commit()                     
    # 🔥
    # Создаем JWT токен
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
        "refresh_token": refresh_token,  # ← отдаем клиенту
        "token_type": "bearer"
    }

@app.get("/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# Защищенный endpoint для теста
@app.get("/protected")
async def protected_route(current_user: models.User = Depends(get_current_user)):
    return {"message": f"Hello {current_user.login}!", "user_id": current_user.id}

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    
    
    openapi_schema = get_openapi(
        title="Auth Service API",
        version="1.0.0",
        description="Microservice for authentication and authorization",
        routes=app.routes,
    )
    
    # Убираем OAuth2 и добавляем простую Bearer схему
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Добавляем security требования ко всем защищенным routes
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if method in ["get", "post", "put", "delete"]:
                if "security" not in openapi_schema["paths"][path][method]:
                    if path not in ["/register", "/login"]:
                        openapi_schema["paths"][path][method]["security"] = [{"Bearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/swagger-auth")
async def swagger_auth(token: str):
    """
    Для Swagger: добавь ?token=YOUR_TOKEN к URL защищенного endpoint
    Пример: /users/me?token=eyJhbGciOiJ...
    """
    return {"message": "Use ?token=YOUR_TOKEN in Swagger requests"}


@app.get("/swagger-links")
async def swagger_links(token: str):
    base_url = "http://localhost:8000"
    return {
        "users_me": f"{base_url}/users/me?token={token}",
        "protected": f"{base_url}/protected?token={token}",
        "usage": "Скопируй ссылку и вставь в браузер или Swagger"
    }




@app.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),  # Это ACCESS token!
    db: Session = Depends(get_db)
):
    # ACCESS token нельзя использовать для поиска refresh токенов!
    # Нужно получить user_id из access token
    payload = utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # Удаляем ВСЕ refresh токены пользователя
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == user_id
    ).delete()
    db.commit()
    
    return {"message": "Successfully logged out"}

@app.get("/users")
async def get_all_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Простой пример - в реальности нужно добавить проверку ролей
    users = db.query(models.User).all()
    return users

@app.put("/profile")
async def update_profile(
    profile_data: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if profile_data.email:
        current_user.email = profile_data.email
    db.commit()
    db.refresh(current_user)
    return current_user





@app.get("/user/stats", response_model=schemas.UserStatsResponse)
async def get_user_stats(
    current_user: models.User = Depends(get_current_user)
):
    """Возвращает статистику пользователя"""
    return {
        "created_at": current_user.created_at,
        "login_count": current_user.login_count, 
        "last_login": current_user.last_login
    }


@app.get("/user/profile", response_model=schemas.UserResponse)
async def get_user_profile(
    current_user: models.User = Depends(get_current_user)
):
    return current_user
    


@app.put("/user/update_password", response_model=schemas.MessageResponse)
async def update_user_password(
    password_data: schemas.PasswordUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Проверяем старый пароль
    if not utils.verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    
    # Хэшируем новый пароль и сохраняем
    current_user.hashed_password = utils.hash_password(password_data.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}


@app.post("/refresh", response_model=schemas.Token)
async def refresh_tokens(
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    # Проверяем валидность refresh токена
    payload = utils.verify_token(refresh_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Проверяем что токен есть в БД и не просрочен
    db_token = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == refresh_token,
        models.RefreshToken.expires_at > datetime.utcnow()
    ).first()
    
    if not db_token:
        raise HTTPException(status_code=401, detail="Refresh token expired or invalid")
    
    user_id = payload.get("sub")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Создаем новую пару токенов
    new_access_token = utils.create_access_token(data={"sub": str(user.id)})
    new_refresh_token = utils.create_refresh_token(data={"sub": str(user.id)})
    
    # Обновляем refresh токен в БД
    db_token.token = new_refresh_token
    db_token.expires_at = datetime.utcnow() + timedelta(days=7)
    db.commit()
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }





@app.get("/admin/users", response_model=List[schemas.UserResponse])
async def get_all_users_admin(
    admin_user: models.User = Depends(dependencies.get_admin_user),
    db: Session = Depends(get_db)
):
    """Получение всех пользователей (только для админов)"""
    users = db.query(models.User).all()
    return users

@app.patch("/admin/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_data: schemas.UserRoleUpdate,
    admin_user: models.User = Depends(dependencies.get_admin_user),
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








@app.post("/send-verification")
async def send_verification(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)  # ← Добавляем зависимость БД
):
    """Отправляет код подтверждения на email"""
    verification_code = utils.generate_verification_code()
    
    # Здесь будет отправка email (пока заглушка)
    print(f"Verification code for {current_user.email}: {verification_code}")
    
    # Сохраняем код в БД
    current_user.verification_code = verification_code
    db.commit()  # ← Теперь db доступна!
    
    return {"message": "Verification code sent"}

@app.post("/verify-email")
async def verify_email(
    code: str = Body(..., embed=True),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)  # ← Должна быть тоже
):
    """Подтверждает email по коду"""
    if current_user.verification_code != code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    current_user.email_verified = True
    current_user.verification_code = None
    db.commit()
    
    return {"message": "Email verified successfully"}







### Валидация токенов
@app.get("/verify")
async def verify_token(
    response: Response,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    if not token:
        raise HTTPException(status_code=401, detail="Token missing")

    if utils.is_token_blacklisted(token):
        raise HTTPException(status_code=401, detail="Token revoked")

    payload = utils.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # 👉 теперь Krakend сможет вытащить X-User-Id
    response.headers["X-User-Id"] = str(user_id)

    return {"id": user.id, "login": user.login}


@app.get("/.well-known/jwks.json")
async def jwks():
    key = base64.urlsafe_b64encode(SECRET_KEY.encode()).decode().rstrip("=")
    return JSONResponse(content={
        "keys": [{
            "kty": "oct",
            "k": key,
            "alg": "HS256",
            "use": "sig"
        }]
    })










if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)