from fastapi import HTTPException, Request
import httpx

async def verify_token(request: Request):
    """Проверка токена через Auth Service"""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    
    token = auth_header[7:]
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://auth-service:8000/verify",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return user_data["id"]
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
                
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Auth service unavailable")