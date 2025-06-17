from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt, create_access_token
from src.models.user import User, Project, ProjectUser
import logging

logger = logging.getLogger(__name__)

def auth_required(permissions=None):
    """
    Decorator to require authentication and optionally check permissions
    
    Args:
        permissions (list): List of required permissions (e.g., ['project:create', 'data:read'])
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Verify JWT token
                verify_jwt_in_request()
                
                # Get user identity from JWT
                current_user_id = get_jwt_identity()
                
                # Get user from database
                user = User.query.filter_by(user_id=current_user_id).first()
                if not user or not user.is_active:
                    logger.warning(f"Invalid or inactive user: {current_user_id}")
                    return jsonify({
                        'code': 'UNAUTHORIZED',
                        'message': 'Invalid or inactive user account',
                        'details': 'Please contact administrator'
                    }), 401
                
                # Extract project_id from URL parameters if present
                project_id = kwargs.get('project_id') or request.view_args.get('project_id')
                
                # If permissions are specified, check them
                if permissions:
                    user_permissions = user.get_permissions()
                    user_projects = user.get_project_ids()
                    
                    # Check if user has required permissions
                    has_permission = any(perm in user_permissions for perm in permissions)
                    
                    # Check if user has access to the project (if project_id is specified)
                    has_project_access = True
                    if project_id:
                        has_project_access = project_id in user_projects or user.is_admin
                    
                    if not (has_permission and has_project_access):
                        logger.warning(f"User {current_user_id} denied access to {request.endpoint} - insufficient permissions")
                        return jsonify({
                            'code': 'FORBIDDEN',
                            'message': 'Insufficient permissions for this action',
                            'details': f'Required permissions: {permissions}'
                        }), 403
                
                # Add user info to request context
                request.current_user = user
                request.current_user_id = current_user_id
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Authentication error: {str(e)}")
                return jsonify({
                    'code': 'UNAUTHORIZED',
                    'message': 'Authentication failed',
                    'details': str(e)
                }), 401
        
        return decorated_function
    return decorator

def create_jwt_token(user):
    """
    Create JWT token with user claims
    
    Args:
        user (User): User object
    
    Returns:
        str: JWT token
    """
    additional_claims = {
        'permissions': user.get_permissions(),
        'projects': user.get_project_ids(),
        'roles': ['admin'] if user.is_admin else [pm.role for pm in user.project_memberships],
        'username': user.username,
        'email': user.email
    }
    
    return create_access_token(
        identity=user.user_id,
        additional_claims=additional_claims
    )

def validate_project_access(user, project_id):
    """
    Validate if user has access to a specific project
    
    Args:
        user (User): User object
        project_id (str): Project ID to check
    
    Returns:
        bool: True if user has access, False otherwise
    """
    if user.is_admin:
        return True
    
    return project_id in user.get_project_ids()

def validate_user_role_in_project(user, project_id, required_roles):
    """
    Validate if user has specific role in a project
    
    Args:
        user (User): User object
        project_id (str): Project ID
        required_roles (list): List of required roles
    
    Returns:
        bool: True if user has required role, False otherwise
    """
    if user.is_admin:
        return True
    
    membership = ProjectUser.query.filter_by(
        user_id=user.user_id,
        project_id=project_id
    ).first()
    
    if not membership:
        return False
    
    return membership.role in required_roles

def sanitize_input(data):
    """
    Sanitize input data to prevent security issues
    
    Args:
        data: Input data to sanitize
    
    Returns:
        Sanitized data
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            clean_key = str(key).replace('<', '').replace('>', '').replace('"', '').replace("'", '')
            sanitized[clean_key] = sanitize_input(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    elif isinstance(data, str):
        # Basic string sanitization
        return data.replace('<script', '&lt;script').replace('</script>', '&lt;/script&gt;')
    else:
        return data

