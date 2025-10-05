from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os

security = HTTPBearer(auto_error=False)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000").rstrip("/")

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Проверяем что пользователь - админ"""
    
    if not credentials:
        raise HTTPException(status_code=302, detail="Not authenticated", headers={"Location": "/admin/login"})
    
    try:
        # Проверяем токен через Auth Service
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/users/me",
                headers={"Authorization": f"Bearer {credentials.credentials}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                # Проверяем что пользователь - админ
                if user_data.get("role") == "admin":
                    return user_data
                
        raise HTTPException(status_code=302, detail="Admin access required", headers={"Location": "/admin/login"})
            
    except Exception as e:
        raise HTTPException(status_code=302, detail="Authentication failed", headers={"Location": "/admin/login"})