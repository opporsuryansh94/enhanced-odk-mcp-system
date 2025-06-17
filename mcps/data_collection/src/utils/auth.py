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
        permissions (list): List of required permissions (e.g., ['data:submit', 'data:read'])
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

def validate_submission_data(data, form_structure=None):
    """
    Validate submission data against form structure
    
    Args:
        data (dict): Submission data to validate
        form_structure (dict): Form structure for validation (optional)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Submission data must be a JSON object"
    
    # Basic validation - ensure required fields are present
    if not data:
        return False, "Submission data cannot be empty"
    
    # TODO: Add more sophisticated validation based on form structure
    # This would involve checking field types, constraints, etc.
    
    return True, None

def sanitize_submission_data(data):
    """
    Sanitize submission data to prevent security issues
    
    Args:
        data (dict): Raw submission data
    
    Returns:
        dict: Sanitized submission data
    """
    if not isinstance(data, dict):
        return {}
    
    sanitized = {}
    
    for key, value in data.items():
        # Sanitize key names (remove potentially dangerous characters)
        clean_key = str(key).replace('<', '').replace('>', '').replace('"', '').replace("'", '')
        
        # Sanitize values based on type
        if isinstance(value, str):
            # Basic string sanitization
            clean_value = value.replace('<script', '&lt;script').replace('</script>', '&lt;/script&gt;')
            sanitized[clean_key] = clean_value
        elif isinstance(value, (int, float, bool)):
            sanitized[clean_key] = value
        elif isinstance(value, list):
            # Recursively sanitize list items
            sanitized[clean_key] = [sanitize_submission_data({'item': item})['item'] if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):
            # Recursively sanitize nested objects
            sanitized[clean_key] = sanitize_submission_data(value)
        else:
            # Convert other types to string and sanitize
            sanitized[clean_key] = str(value)
    
    return sanitized

