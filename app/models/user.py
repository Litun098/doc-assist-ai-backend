"""
User model for the application.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """User model."""
    id: str
    email: str
    full_name: Optional[str] = None
    subscription_tier: Optional[str] = "free"
