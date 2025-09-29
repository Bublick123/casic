from fastapi import FastAPI, Depends, Request, Header
from strawberry.fastapi import GraphQLRouter
from sqlalchemy.orm import Session
from . import models
from .database import engine, get_db
from .schema import schema
from .dependencies import get_current_user_id
import logging

logging.basicConfig(level=logging.INFO)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Wallet Service", version="1.0.0")

async def get_context(
    request: Request, 
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    print("=== DEBUG GET_CONTEXT ===")
    print(f"Authorization header: {authorization}")
    
    user_id = None
    try:
        user_id = await get_current_user_id(authorization)
        print(f"Successfully authenticated user_id: {user_id}")
    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        user_id = None
    
    print(f"Final user_id: {user_id}")
    print("========================")
    
    return {
        "db": db,
        "user_id": user_id,
        "request": request
    }

graphql_app = GraphQLRouter(schema, context_getter=get_context)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/")
async def root():
    return {"message": "Wallet Service is running!"}