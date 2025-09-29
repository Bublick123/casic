from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .dependencies import verify_token
from .utils import proxy_request
from httpx import AsyncClient
import httpx
app = FastAPI(title="API Gateway")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/auth/{path:path}")
async def proxy_auth(path: str, request: Request):
    """Проксирование запросов к Auth Service"""
    target_url = f"http://auth-service:8000/{path}"
    response = await proxy_request(target_url, request)
    return response.json()

@app.post("/graphql")
async def proxy_graphql(request: Request, user_id: str = Depends(verify_token)):
    """Проксирование запросов к Wallet Service с аутентификацией"""
    target_url = "http://wallet-service:8000/graphql"
    
    # Получаем тело запроса
    body = await request.body()
    
    # Подготавливаем заголовки ДЛЯ ЗАПРОСА к Wallet Service
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in ["host", "content-length"]
    }
    # Добавляем user_id в заголовки ДЛЯ ЗАПРОСА
    headers["X-User-Id"] = str(user_id)
    
    # Проксируем запрос
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers,  # ← Используем наши заголовки с X-User-Id
                params=request.query_params,
                timeout=30.0
            )
            
            # ВОЗВРАЩАЕМ ОТВЕТ КАК ЕСТЬ БЕЗ ИЗМЕНЕНИЯ ЗАГОЛОВКОВ!
            # Просто возвращаем JSON ответ
            return response.json()
            
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Wallet service unavailable")

@app.get("/health")
async def health_check():
    """Health check для Gateway"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)