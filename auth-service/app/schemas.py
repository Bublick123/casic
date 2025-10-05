from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional
from datetime import datetime
class UserCreate(BaseModel):
   
    login: str
    email: EmailStr        
    password: str

class UserLogin(BaseModel):
   
    login: str    
    password: str

     
class UserResponse(BaseModel):
    id: int
    login: str
    email: EmailStr
    last_login: Optional[datetime] = None 
    created_at: datetime
    role: str = "user"
    email_verified: bool
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str  # ← Добавляем!
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None

class UserList(BaseModel):
    id: int
    login: str
    email: EmailStr
    
    class Config:
        from_attributes = True





class UserStatsResponse(BaseModel):                 
    created_at: datetime
    login_count: int
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class PasswordUpdateRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)

    @model_validator(mode="before")
    def passwords_must_differ(cls, values):
        old = values.get("old_password")
        new = values.get("new_password")
        if old == new:
            raise ValueError("New password must be different from old password")
        return values


class MessageResponse(BaseModel):
    message: str


class UserRoleUpdate(BaseModel):
    role: str = "user"



