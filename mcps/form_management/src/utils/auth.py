from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
import requests
import logging

logger = logging.getLogger(__name__)

def auth_required(permissions=None):
    """
    Decorator to require authentication and optionally check permissions
    
    Args:
        permissions (list): List of required permissions (e.g., ['form:create', 'project:manage'])
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Verify JWT token
                verify_jwt_in_request()
                
                # Get user identity and claims from JWT
                current_user = get_jwt_identity()
                jwt_claims = get_jwt()
                
                # Extract project_id from URL parameters if present
                project_id = kwargs.get('project_id') or request.view_args.get('project_id')
                
                # If permissions are specified, check them
                if permissions:
                    user_permissions = jwt_claims.get('permissions', [])
                    user_projects = jwt_claims.get('projects', [])
                    
                    # Check if user has required permissions
                    has_permission = any(perm in user_permissions for perm in permissions)
                    
                    # Check if user has access to the project (if project_id is specified)
                    has_project_access = True
                    if project_id:
                        has_project_access = project_id in user_projects or 'admin' in jwt_claims.get('roles', [])
                    
                    if not (has_permission and has_project_access):
                        logger.warning(f"User {current_user} denied access to {request.endpoint} - insufficient permissions")
                        return jsonify({
                            'code': 'FORBIDDEN',
                            'message': 'Insufficient permissions for this action',
                            'details': f'Required permissions: {permissions}'
                        }), 403
                
                # Add user info to request context
                request.current_user = current_user
                request.jwt_claims = jwt_claims
                
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

def validate_project_access(project_id, user_claims):
    """
    Validate if user has access to a specific project
    
    Args:
        project_id (str): Project ID to check
        user_claims (dict): JWT claims containing user permissions and projects
    
    Returns:
        bool: True if user has access, False otherwise
    """
    user_projects = user_claims.get('projects', [])
    user_roles = user_claims.get('roles', [])
    
    # Admin users have access to all projects
    if 'admin' in user_roles:
        return True
    
    # Check if user is explicitly assigned to the project
    return project_id in user_projects

