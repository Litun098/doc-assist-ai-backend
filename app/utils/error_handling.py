"""
Error handling utilities.
"""
import logging
import traceback
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base class for application errors."""
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an error with context.
    
    Args:
        error: The exception to log
        context: Additional context for the error
    """
    error_type = type(error).__name__
    error_message = str(error)
    error_traceback = traceback.format_exc()
    
    log_data = {
        "error_type": error_type,
        "error_message": error_message,
        "traceback": error_traceback,
    }
    
    if context:
        log_data.update(context)
    
    logger.error(f"Error: {error_type} - {error_message}", extra=log_data)

def format_error_response(error: Exception) -> Dict[str, Any]:
    """
    Format an error for API response.
    
    Args:
        error: The exception to format
        
    Returns:
        Dictionary with error details
    """
    if isinstance(error, AppError):
        return {
            "error": error.message,
            "status_code": error.status_code,
            "details": error.details,
        }
    else:
        return {
            "error": str(error),
            "status_code": 500,
            "details": {},
        }
