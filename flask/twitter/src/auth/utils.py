"""
Authentication utilities for JWT token handling and user authentication
"""
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import current_app, request, jsonify, g
from ..models import User, db
import secrets
import hashlib


class AuthManager:
    """Centralized authentication management"""

    @staticmethod
    def generate_tokens(user_id: int):
        """Generate access and refresh tokens for a user"""
        payload = {
            'user_id': user_id,
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),  # 1 hour expiry
            'iat': datetime.now(timezone.utc),
            'type': 'access'
        }

        refresh_payload = {
            'user_id': user_id,
            'exp': datetime.now(timezone.utc) + timedelta(days=30),  # 30 days expiry
            'iat': datetime.now(timezone.utc),
            'type': 'refresh'
        }

        access_token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
        refresh_token = jwt.encode(refresh_payload, current_app.config['SECRET_KEY'], algorithm='HS256')

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': 3600,  # 1 hour in seconds
            'token_type': 'Bearer'
        }

    @staticmethod
    def verify_token(token: str, token_type: str = 'access'):
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])

            if payload.get('type') != token_type:
                return None

            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def get_current_user():
        """Get current authenticated user from request context"""
        return getattr(g, 'current_user', None)


def token_required(f):
    """Decorator to require valid JWT token for API access"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        # Verify token
        payload = AuthManager.verify_token(token)
        if not payload:
            return jsonify({'error': 'Token is invalid or expired'}), 401

        # Get user
        user = User.query.get(payload['user_id'])
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401

        # Set current user in request context
        g.current_user = user

        return f(*args, **kwargs)

    return decorated


def optional_auth(f):
    """Decorator for optional authentication (user can be None)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                pass

        if token:
            # Verify token
            payload = AuthManager.verify_token(token)
            if payload:
                user = User.query.get(payload['user_id'])
                if user and user.is_active:
                    g.current_user = user

        # Set None if no valid token
        if not hasattr(g, 'current_user'):
            g.current_user = None

        return f(*args, **kwargs)

    return decorated


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username: str) -> bool:
    """Username validation"""
    import re
    # Username must be 3-50 characters, alphanumeric with underscores
    pattern = r'^[a-zA-Z0-9_]{3,50}$'
    return re.match(pattern, username) is not None


def validate_password(password: str) -> tuple[bool, str]:
    """Password validation with detailed feedback"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if len(password) > 128:
        return False, "Password must be less than 128 characters"

    # Check for at least one digit, one lowercase, one uppercase
    has_digit = any(char.isdigit() for char in password)
    has_lower = any(char.islower() for char in password)
    has_upper = any(char.isupper() for char in password)

    if not (has_digit and has_lower and has_upper):
        return False, "Password must contain at least one digit, one lowercase and one uppercase letter"

    return True, "Password is valid"


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self):
        self.requests = {}

    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed based on rate limit"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window)

        # Clean old requests
        if key in self.requests:
            self.requests[key] = [req_time for req_time in self.requests[key] if req_time > window_start]
        else:
            self.requests[key] = []

        # Check limit
        if len(self.requests[key]) >= limit:
            return False

        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(limit: int = 100, window: int = 3600):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Use IP address as key, or user ID if authenticated
            key = request.remote_addr
            if hasattr(g, 'current_user') and g.current_user:
                key = f"user_{g.current_user.id}"

            if not rate_limiter.is_allowed(key, limit, window):
                return jsonify({'error': 'Rate limit exceeded'}), 429

            return f(*args, **kwargs)
        return decorated
    return decorator