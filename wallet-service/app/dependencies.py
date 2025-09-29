import os
from fastapi import HTTPException, Header
from httpx import AsyncClient
import logging

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")

async def get_current_user_id(authorization: str = Header(None)):
    print("=== DEBUG GET_CURRENT_USER_ID ===")
    print(f"Received authorization: {authorization}")
    
    if not authorization or not authorization.startswith("Bearer "):
        print("Missing or invalid authorization header")
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = authorization[7:]
    print(f"Token: {token}")

    async with AsyncClient() as client:
        try:
            print(f"Calling auth service: {AUTH_SERVICE_URL}/verify")
            response = await client.get(
                f"{AUTH_SERVICE_URL}/verify",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0
            )
            print(f"Auth service response status: {response.status_code}")
            print(f"Auth service response body: {response.text}")
            
            response.raise_for_status()
            user_data = response.json()
            print(f"User data from auth: {user_data}")
            
            user_id = user_data.get("id")
            print(f"Extracted user_id: {user_id}")
            
            return user_id
            
        except Exception as e:
            print(f"Auth service call failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication failed")