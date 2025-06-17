from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User
from src.utils.auth import create_jwt_token, sanitize_input
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        if not request.is_json:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'Content-Type must be application/json',
                'details': 'User data must be provided as JSON'
            }), 400
        
        data = sanitize_input(request.get_json())
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'code': 'BAD_REQUEST',
                    'message': f'Missing required field: {field}',
                    'details': f'{field} is required for registration'
                }), 400
        
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        
        if existing_user:
            return jsonify({
                'code': 'CONFLICT',
                'message': 'User already exists',
                'details': 'Username or email already registered'
            }), 409
        
        # Create new user
        new_user = User(
            username=data['username'],
            email=data['email'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', '')
        )
        
        new_user.set_password(data['password'])
        
        db.session.add(new_user)
        db.session.commit()
        
        logger.info(f"New user registered: {new_user.username}")
        
        return jsonify({
            'user_id': new_user.user_id,
            'username': new_user.username,
            'message': 'User registered successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        db.session.rollback()
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Registration failed',
            'details': str(e)
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate a user and issue a JWT"""
    try:
        if not request.is_json:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'Content-Type must be application/json',
                'details': 'Credentials must be provided as JSON'
            }), 400
        
        data = sanitize_input(request.get_json())
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'Missing credentials',
                'details': 'Username and password are required'
            }), 400
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not user.check_password(password):
            logger.warning(f"Failed login attempt for: {username}")
            return jsonify({
                'code': 'UNAUTHORIZED',
                'message': 'Invalid credentials',
                'details': 'Username or password is incorrect'
            }), 401
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {username}")
            return jsonify({
                'code': 'UNAUTHORIZED',
                'message': 'Account inactive',
                'details': 'Please contact administrator'
            }), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Create JWT token
        access_token = create_jwt_token(user)
        
        logger.info(f"Successful login: {user.username}")
        
        return jsonify({
            'access_token': access_token,
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin,
            'permissions': user.get_permissions(),
            'projects': user.get_project_ids()
        }), 200
        
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Login failed',
            'details': str(e)
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Invalidate a user's session/token"""
    try:
        # In a more sophisticated implementation, you would maintain a blacklist
        # of invalidated tokens. For now, we'll just return success.
        current_user_id = get_jwt_identity()
        
        logger.info(f"User logged out: {current_user_id}")
        
        return jsonify({
            'message': 'Logged out successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Logout failed',
            'details': str(e)
        }), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user's profile"""
    try:
        current_user_id = get_jwt_identity()
        
        user = User.query.filter_by(user_id=current_user_id).first()
        if not user:
            return jsonify({
                'code': 'NOT_FOUND',
                'message': 'User not found',
                'details': 'Current user account not found'
            }), 404
        
        return jsonify(user.to_dict(include_sensitive=True)), 200
        
    except Exception as e:
        logger.error(f"Error retrieving current user: {str(e)}")
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to retrieve user profile',
            'details': str(e)
        }), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change current user's password"""
    try:
        if not request.is_json:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'Content-Type must be application/json',
                'details': 'Password data must be provided as JSON'
            }), 400
        
        data = sanitize_input(request.get_json())
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'Missing password fields',
                'details': 'Both current_password and new_password are required'
            }), 400
        
        current_user_id = get_jwt_identity()
        user = User.query.filter_by(user_id=current_user_id).first()
        
        if not user:
            return jsonify({
                'code': 'NOT_FOUND',
                'message': 'User not found',
                'details': 'Current user account not found'
            }), 404
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({
                'code': 'UNAUTHORIZED',
                'message': 'Invalid current password',
                'details': 'Current password is incorrect'
            }), 401
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        logger.info(f"Password changed for user: {user.username}")
        
        return jsonify({
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        db.session.rollback()
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to change password',
            'details': str(e)
        }), 500

