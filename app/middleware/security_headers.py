"""
Middleware for adding security headers to responses.
"""
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable

from config.config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to the response.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response with security headers added
        """
        response = await call_next(request)

        # Check if the request is for the docs
        is_docs_request = request.url.path in ['/docs', '/redoc', '/openapi.json']

        if is_docs_request:
            # More permissive CSP for documentation pages
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: blob: https://fastapi.tiangolo.com; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self' https://*.supabase.co https://*.openai.com; "
                "frame-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self';"
            )
        else:
            # Standard CSP for other pages
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self'; "
                "connect-src 'self' https://*.supabase.co https://*.openai.com; "
                "frame-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self';"
            )

        # X-Content-Type-Options
        # Prevents browsers from MIME-sniffing a response away from the declared content-type
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer-Policy
        # Controls how much referrer information should be included with requests
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # X-XSS-Protection
        # Enables the Cross-site scripting (XSS) filter in browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # X-Frame-Options
        # Prevents the page from being displayed in an iframe
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # Strict-Transport-Security
        # Enforces HTTPS usage (only in production)
        if getattr(settings, 'ENVIRONMENT', 'development') != "development":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Permissions-Policy
        # Controls which browser features and APIs can be used
        response.headers["Permissions-Policy"] = (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "interest-cohort=()"
        )

        return response

def add_security_headers_middleware(app: FastAPI) -> None:
    """
    Add security headers middleware to the FastAPI application.

    Args:
        app: The FastAPI application
    """
    app.add_middleware(SecurityHeadersMiddleware)
