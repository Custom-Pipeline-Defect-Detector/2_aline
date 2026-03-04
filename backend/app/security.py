from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib
from fastapi import HTTPException, status, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
import re

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_TIME = 300  # 5 minutes
CSRF_TOKEN_LENGTH = 32
PASSWORD_MIN_LENGTH = 8

# Common passwords to check against (simplified for this example)
COMMON_PASSWORDS = {
    "password", "12345678", "qwerty", "abc123", "password123",
    "admin", "letmein", "welcome", "monkey", "dragon"
}

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validates password strength based on security requirements.
    
    Args:
        password: The password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
    
    if password.lower() in COMMON_PASSWORDS:
        return False, "Password is too common and not allowed"
    
    # Check for at least one uppercase, lowercase, digit, and special character
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if not (has_upper and has_lower and has_digit and has_special):
        return False, "Password must contain uppercase, lowercase, digit, and special character"
    
    return True, ""

def sanitize_input(input_str: str) -> str:
    """
    Sanitizes user input to prevent XSS and other injection attacks.
    
    Args:
        input_str: The input string to sanitize
        
    Returns:
        Sanitized string
    """
    if not input_str:
        return input_str
    
    # Remove potentially dangerous characters
    sanitized = input_str.strip()
    
    # Prevent script tags
    sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
    
    return sanitized

def generate_csrf_token() -> str:
    """
    Generates a secure CSRF token.
    
    Returns:
        A random CSRF token
    """
    return secrets.token_hex(CSRF_TOKEN_LENGTH)

def verify_csrf_token(token: str, expected_token: str) -> bool:
    """
    Verifies a CSRF token.
    
    Args:
        token: The token to verify
        expected_token: The expected token
        
    Returns:
        True if valid, False otherwise
    """
    if not token or not expected_token:
        return False
    return secrets.compare_digest(token, expected_token)

def hash_csrf_token(token: str) -> str:
    """
    Hashes a CSRF token for secure storage.
    
    Args:
        token: The token to hash
        
    Returns:
        Hashed token
    """
    return hashlib.sha256(token.encode()).hexdigest()

def is_valid_email(email: str) -> bool:
    """
    Validates email format.
    
    Args:
        email: The email to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_safe_filename(filename: str) -> bool:
    """
    Checks if a filename is safe to use.
    
    Args:
        filename: The filename to check
        
    Returns:
        True if safe, False otherwise
    """
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Check for potentially dangerous extensions
    dangerous_extensions = ['.exe', '.bat', '.sh', '.php', '.jsp', '.asp']
    if any(filename.lower().endswith(ext) for ext in dangerous_extensions):
        return False
    
    # Check for valid filename characters
    invalid_chars = '<>:"/\\|?*'
    if any(char in invalid_chars for char in filename):
        return False
    
    return True

async def security_middleware(request: Request, call_next):
    """
    Security middleware to add security headers and perform basic security checks.
    """
    # Add security headers
    response = await call_next(request)
    
    # Add security headers to response
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response

def check_rate_limit(request: Request) -> bool:
    """
    Check if the request exceeds rate limits.
    This is a simplified version - in practice, you'd use the slowapi decorator.
    """
    # This would typically be handled by slowapi decorators
    # This function is here for demonstration purposes
    return True