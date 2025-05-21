"""
Middleware for rate limiting requests.
"""
import time
import logging
from fastapi import FastAPI, Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, List, Callable, Optional
from datetime import datetime

from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter implementation."""
    
    def __init__(self, limit: int, window: int):
        """
        Initialize the rate limiter.
        
        Args:
            limit: Maximum number of requests allowed in the window
            window: Time window in seconds
        """
        self.limit = limit
        self.window = window
        self.requests: Dict[str, List[float]] = {}
    
    def is_rate_limited(self, key: str) -> bool:
        """
        Check if a key is rate limited.
        
        Args:
            key: The key to check (usually an IP address)
            
        Returns:
            True if rate limited, False otherwise
        """
        current_time = time.time()
        
        # Initialize if key doesn't exist
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove requests outside the window
        self.requests[key] = [t for t in self.requests[key] if current_time - t < self.window]
        
        # Check if limit is reached
        if len(self.requests[key]) >= self.limit:
            return True
        
        # Add current request
        self.requests[key].append(current_time)
        return False
    
    def get_remaining(self, key: str) -> int:
        """
        Get the number of remaining requests for a key.
        
        Args:
            key: The key to check
            
        Returns:
            Number of remaining requests
        """
        if key not in self.requests:
            return self.limit
        
        current_time = time.time()
        valid_requests = [t for t in self.requests[key] if current_time - t < self.window]
        return max(0, self.limit - len(valid_requests))

# Create rate limiters
login_rate_limiter = RateLimiter(
    limit=settings.LOGIN_RATE_LIMIT,
    window=settings.LOGIN_RATE_LIMIT_WINDOW
)

api_rate_limiter = RateLimiter(
    limit=settings.API_RATE_LIMIT,
    window=settings.API_RATE_LIMIT_WINDOW
)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Rate limit requests based on client IP and path.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            The response
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Determine which rate limiter to use based on the path
        path = request.url.path
        
        # Apply stricter rate limiting for authentication endpoints
        if path.startswith("/api/auth/login") or path.startswith("/api/auth/register"):
            rate_limiter = login_rate_limiter
            rate_limit_key = f"{client_ip}:{path}"
            
            if rate_limiter.is_rate_limited(rate_limit_key):
                logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
                
                # Log the security event
                self._log_security_event(
                    event_type="rate_limit_exceeded",
                    client_ip=client_ip,
                    path=path,
                    details="Authentication rate limit exceeded"
                )
                
                return Response(
                    content='{"detail":"Too many login attempts. Please try again later."}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json",
                    headers={
                        "Retry-After": str(settings.LOGIN_RATE_LIMIT_WINDOW),
                        "X-RateLimit-Limit": str(settings.LOGIN_RATE_LIMIT),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time() + settings.LOGIN_RATE_LIMIT_WINDOW))
                    }
                )
        else:
            # General API rate limiting
            rate_limiter = api_rate_limiter
            rate_limit_key = client_ip
            
            if rate_limiter.is_rate_limited(rate_limit_key):
                logger.warning(f"API rate limit exceeded for {client_ip}")
                
                # Log the security event
                self._log_security_event(
                    event_type="rate_limit_exceeded",
                    client_ip=client_ip,
                    path=path,
                    details="API rate limit exceeded"
                )
                
                return Response(
                    content='{"detail":"Too many requests. Please try again later."}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json",
                    headers={
                        "Retry-After": str(settings.API_RATE_LIMIT_WINDOW),
                        "X-RateLimit-Limit": str(settings.API_RATE_LIMIT),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time() + settings.API_RATE_LIMIT_WINDOW))
                    }
                )
        
        # Add rate limit headers to the response
        response = await call_next(request)
        remaining = rate_limiter.get_remaining(rate_limit_key)
        
        response.headers["X-RateLimit-Limit"] = str(rate_limiter.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + rate_limiter.window))
        
        return response
    
    def _log_security_event(self, event_type: str, client_ip: str, path: str, details: Optional[str] = None) -> None:
        """
        Log a security event.
        
        Args:
            event_type: Type of security event
            client_ip: Client IP address
            path: Request path
            details: Additional details
        """
        logger.warning(
            f"Security event: {event_type} | IP: {client_ip} | Path: {path} | Details: {details or 'N/A'}"
        )

def add_rate_limit_middleware(app: FastAPI) -> None:
    """
    Add rate limit middleware to the FastAPI application.
    
    Args:
        app: The FastAPI application
    """
    app.add_middleware(RateLimitMiddleware)
