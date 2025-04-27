"""
Authentication routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.services.auth_service import auth_service

router = APIRouter()

class UserCreate(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str

@router.post("/register")
async def register(user_data: UserCreate):
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        
    Returns:
        User information and access token
    """
    return await auth_service.register_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )

@router.post("/login")
async def login(user_data: UserLogin):
    """
    Login a user.
    
    Args:
        user_data: User login data
        
    Returns:
        User information and access token
    """
    return await auth_service.login_user(
        email=user_data.email,
        password=user_data.password
    )

@router.get("/me")
async def get_current_user(current_user = Depends(auth_service.get_current_user)):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user (from dependency)
        
    Returns:
        User information
    """
    return current_user
