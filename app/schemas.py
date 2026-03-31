from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr


class UserRead(BaseModel):
    id: str
    name: str
    email: EmailStr

    model_config = {"from_attributes": True}


class SessionCreate(BaseModel):
    user_id: str
    title: str | None = None


class SessionRead(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    title: str

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    session_id: str
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1)


class MessageRead(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    user_name: str
    user_email: EmailStr
    session_id: str | None = None
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    tool_trace: list[dict] = Field(default_factory=list)

