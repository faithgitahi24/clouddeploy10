from typing import Optional
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(unique=True)
    full_name: str
    password: str
    is_admin: bool = False


class UserRegister(SQLModel):
    username: str
    email: str
    full_name: str
    password: str


class UserLogin(SQLModel):
    username: str
    password: str


class UserResponse(SQLModel):
    id: int
    username: str
    email: str
    full_name: str