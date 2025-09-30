from fastapi import Depends, HTTPException, status, Header
import httpx
from typing import Optional

AUTH_SERVICE_URL = "http://auth-service:8000"

async def verify_token(authorization: str = Header(None)) -> int:
    """Верифицирует JWT токен и возвращает user_id"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization[7:]
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/verify",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return user_data["id"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
                
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auth service unavailable"
            )

async def get_current_user_id(user_id: int = Depends(verify_token)) -> int:
    """Возвращает ID текущего пользователя"""
    return user_id