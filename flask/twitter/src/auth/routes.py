"""
Authentication routes for user registration, login, logout, and token management
"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime, timezone
from ..models import User, db
from .utils import (
    AuthManager, token_required, validate_email, validate_username,
    validate_password, rate_limit
)

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['POST'])
@rate_limit(limit=5, window=3600)  # 5 registrations per hour
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400

        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        display_name = data.get('display_name', '').strip()

        # Validate input
        if not validate_username(username):
            return jsonify({
                'error': 'Username must be 3-50 characters long and contain only letters, numbers, and underscores'
            }), 400

        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        is_valid, password_message = validate_password(password)
        if not is_valid:
            return jsonify({'error': password_message}), 400

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 409

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409

        # Create new user
        user = User(
            username=username,
            email=email,
            password=password,
            display_name=display_name or username
        )

        db.session.add(user)
        db.session.commit()

        # Generate tokens
        tokens = AuthManager.generate_tokens(user.id)

        return jsonify({
            'message': 'User registered successfully',
            'user': user.serialize(),
            **tokens
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed', 'details': str(e)}), 500


@bp.route('/login', methods=['POST'])
@rate_limit(limit=10, window=900)  # 10 login attempts per 15 minutes
def login():
    """User login endpoint"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields
        identifier = data.get('username') or data.get('email')
        password = data.get('password')

        if not identifier or not password:
            return jsonify({'error': 'Username/email and password are required'}), 400

        # Find user by username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401

        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        # Generate tokens
        tokens = AuthManager.generate_tokens(user.id)

        return jsonify({
            'message': 'Login successful',
            'user': user.serialize(include_private=True),
            **tokens
        }), 200

    except Exception as e:
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500


@bp.route('/refresh', methods=['POST'])
@rate_limit(limit=20, window=3600)  # 20 refresh attempts per hour
def refresh_token():
    """Refresh access token using refresh token"""
    try:
        data = request.get_json()

        if not data or 'refresh_token' not in data:
            return jsonify({'error': 'Refresh token is required'}), 400

        refresh_token = data['refresh_token']

        # Verify refresh token
        payload = AuthManager.verify_token(refresh_token, token_type='refresh')
        if not payload:
            return jsonify({'error': 'Invalid or expired refresh token'}), 401

        # Get user
        user = User.query.get(payload['user_id'])
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401

        # Generate new tokens
        tokens = AuthManager.generate_tokens(user.id)

        return jsonify({
            'message': 'Token refreshed successfully',
            **tokens
        }), 200

    except Exception as e:
        return jsonify({'error': 'Token refresh failed', 'details': str(e)}), 500


@bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """User logout endpoint"""
    # In a production system, you would maintain a blacklist of tokens
    # For simplicity, we just return success
    return jsonify({'message': 'Logout successful'}), 200


@bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """Get current authenticated user information"""
    user = AuthManager.get_current_user()
    return jsonify({
        'user': user.serialize(include_private=True)
    }), 200


@bp.route('/me', methods=['PUT'])
@token_required
def update_current_user():
    """Update current user's profile"""
    try:
        user = AuthManager.get_current_user()
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update allowed fields
        updatable_fields = ['display_name', 'bio', 'location', 'website']
        updated = False

        for field in updatable_fields:
            if field in data:
                value = data[field]
                if value is not None:
                    value = str(value).strip()

                # Validate field lengths
                if field == 'display_name' and value and len(value) > 100:
                    return jsonify({'error': 'Display name must be less than 100 characters'}), 400
                elif field == 'bio' and value and len(value) > 500:
                    return jsonify({'error': 'Bio must be less than 500 characters'}), 400
                elif field == 'location' and value and len(value) > 100:
                    return jsonify({'error': 'Location must be less than 100 characters'}), 400
                elif field == 'website' and value and len(value) > 200:
                    return jsonify({'error': 'Website must be less than 200 characters'}), 400

                setattr(user, field, value or None)
                updated = True

        if updated:
            user.updated_at = datetime.now(timezone.utc)
            db.session.commit()

        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.serialize(include_private=True)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Profile update failed', 'details': str(e)}), 500


@bp.route('/change-password', methods=['POST'])
@token_required
@rate_limit(limit=5, window=3600)  # 5 password changes per hour
def change_password():
    """Change user password"""
    try:
        user = AuthManager.get_current_user()
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not current_password or not new_password:
            return jsonify({'error': 'Current password and new password are required'}), 400

        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Validate new password
        is_valid, password_message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': password_message}), 400

        # Update password
        user.set_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({'message': 'Password changed successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Password change failed', 'details': str(e)}), 500


@bp.route('/deactivate', methods=['POST'])
@token_required
def deactivate_account():
    """Deactivate user account"""
    try:
        user = AuthManager.get_current_user()
        data = request.get_json()

        if not data or 'password' not in data:
            return jsonify({'error': 'Password confirmation is required'}), 400

        # Verify password
        if not user.check_password(data['password']):
            return jsonify({'error': 'Incorrect password'}), 401

        # Deactivate account
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({'message': 'Account deactivated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Account deactivation failed', 'details': str(e)}), 500