import httpx
from fastapi import HTTPException, Request

async def proxy_request(target_url: str, request: Request):
    """Проксирование запроса на целевой сервис"""
    body = await request.body()
    
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in ["host", "content-length"]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Используем content для любых данных
            response = await client.request(
                method=request.method,
                url=target_url,
                content=body,  # ← Правильный способ!
                headers=headers,
                params=request.query_params,
                timeout=30.0
            )
            return response
            
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Service unavailable")