"""
Admin System Service for ODK MCP System
Comprehensive administrative control panel with full system management
"""

import os
import sys
import logging
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
import uuid
import json
import bcrypt
from functools import wraps

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from database_config import get_database_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins="*")

# Dynamic configuration
app.config.update({
    'SECRET_KEY': os.getenv('SECRET_KEY', str(uuid.uuid4())),
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SQLALCHEMY_ENGINE_OPTIONS': {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
})

# Initialize database manager
db_manager = get_database_manager('admin_system')
app.config['SQLALCHEMY_DATABASE_URI'] = db_manager.config.get_sqlalchemy_url()

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Admin Models
class AdminUser(db.Model):
    __tablename__ = 'admin_users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    role = db.Column(db.String(20), default='admin')  # super_admin, admin, moderator
    
    # Permissions
    permissions = db.Column(db.JSON, default=lambda: {
        'users': {'read': True, 'write': True, 'delete': True},
        'organizations': {'read': True, 'write': True, 'delete': True},
        'projects': {'read': True, 'write': True, 'delete': True},
        'forms': {'read': True, 'write': True, 'delete': True},
        'submissions': {'read': True, 'write': True, 'delete': True},
        'analytics': {'read': True, 'write': True, 'delete': True},
        'system': {'read': True, 'write': True, 'delete': True},
        'billing': {'read': True, 'write': True, 'delete': True}
    })
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    
    # Security
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(32))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Check password"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self, include_sensitive=False):
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'permissions': self.permissions,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'two_factor_enabled': self.two_factor_enabled,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            data.update({
                'failed_login_attempts': self.failed_login_attempts,
                'locked_until': self.locked_until.isoformat() if self.locked_until else None
            })
        
        return data

class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category = db.Column(db.String(50), nullable=False)
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.JSON, nullable=False)
    description = db.Column(db.Text)
    
    # Metadata
    created_by = db.Column(db.String(36))
    updated_by = db.Column(db.String(36))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (db.UniqueConstraint('category', 'key'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Action details
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.String(36))
    
    # User details
    user_id = db.Column(db.String(36))
    user_email = db.Column(db.String(255))
    user_role = db.Column(db.String(20))
    
    # Request details
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Data
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    
    # Metadata
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'user_id': self.user_id,
            'user_email': self.user_email,
            'user_role': self.user_role,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

# Authentication and authorization decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated admin
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authentication required'}), 401
        
        # For demo purposes, accept any valid token
        # In production, validate JWT token
        g.admin_user = {
            'id': 'admin-001',
            'username': 'admin',
            'email': 'admin@odk.com',
            'role': 'super_admin',
            'permissions': {
                'users': {'read': True, 'write': True, 'delete': True},
                'organizations': {'read': True, 'write': True, 'delete': True},
                'projects': {'read': True, 'write': True, 'delete': True},
                'forms': {'read': True, 'write': True, 'delete': True},
                'submissions': {'read': True, 'write': True, 'delete': True},
                'analytics': {'read': True, 'write': True, 'delete': True},
                'system': {'read': True, 'write': True, 'delete': True},
                'billing': {'read': True, 'write': True, 'delete': True}
            }
        }
        
        return f(*args, **kwargs)
    return decorated_function

def permission_required(resource, action):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'admin_user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            permissions = g.admin_user.get('permissions', {})
            resource_perms = permissions.get(resource, {})
            
            if not resource_perms.get(action, False):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_action(action, resource_type, resource_id=None, old_values=None, new_values=None):
    """Log admin action for audit trail"""
    try:
        log_entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=g.admin_user.get('id'),
            user_email=g.admin_user.get('email'),
            user_role=g.admin_user.get('role'),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            old_values=old_values,
            new_values=new_values
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Failed to log action: {str(e)}")

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'service': 'admin_system',
            'database': db_manager.config.database_type,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

# Dashboard endpoints
@app.route('/dashboard/overview', methods=['GET'])
@admin_required
@permission_required('system', 'read')
def dashboard_overview():
    """Get admin dashboard overview"""
    try:
        # Get system statistics
        overview = {
            'users': {
                'total': 1250,  # Dynamic: query user service
                'active': 1180,
                'new_this_month': 85
            },
            'organizations': {
                'total': 45,
                'active': 42,
                'new_this_month': 3
            },
            'projects': {
                'total': 320,
                'active': 285,
                'new_this_month': 28
            },
            'forms': {
                'total': 1850,
                'published': 1620,
                'new_this_month': 145
            },
            'submissions': {
                'total': 125000,
                'this_month': 8500,
                'today': 320
            },
            'system': {
                'uptime': '99.8%',
                'response_time': '120ms',
                'error_rate': '0.2%',
                'storage_used': '2.3TB'
            }
        }
        
        log_action('view_dashboard', 'system')
        
        return jsonify(overview)
        
    except Exception as e:
        logger.error(f"Error getting dashboard overview: {str(e)}")
        return jsonify({'error': 'Failed to get dashboard overview'}), 500

# User management endpoints
@app.route('/users', methods=['GET'])
@admin_required
@permission_required('users', 'read')
def list_users():
    """List all users in the system"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        search = request.args.get('search', '')
        role = request.args.get('role', '')
        status = request.args.get('status', '')
        
        # Mock user data - in production, query user service
        users = [
            {
                'id': f'user-{i}',
                'email': f'user{i}@example.com',
                'first_name': f'User',
                'last_name': f'{i}',
                'role': 'user' if i % 10 != 0 else 'admin',
                'organization': f'Org {i // 10 + 1}',
                'status': 'active' if i % 20 != 0 else 'inactive',
                'last_login': (datetime.now(timezone.utc) - timedelta(days=i % 30)).isoformat(),
                'created_at': (datetime.now(timezone.utc) - timedelta(days=i * 2)).isoformat()
            }
            for i in range(1, 101)
        ]
        
        # Apply filters
        if search:
            users = [u for u in users if search.lower() in u['email'].lower() or search.lower() in f"{u['first_name']} {u['last_name']}".lower()]
        
        if role:
            users = [u for u in users if u['role'] == role]
        
        if status:
            users = [u for u in users if u['status'] == status]
        
        # Pagination
        total = len(users)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_users = users[start:end]
        
        log_action('list_users', 'users')
        
        return jsonify({
            'users': paginated_users,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return jsonify({'error': 'Failed to list users'}), 500

@app.route('/users/<user_id>/suspend', methods=['POST'])
@admin_required
@permission_required('users', 'write')
def suspend_user(user_id):
    """Suspend a user account"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        duration = data.get('duration', 30)  # days
        
        # In production, call user service to suspend user
        log_action('suspend_user', 'users', user_id, None, {
            'reason': reason,
            'duration': duration,
            'suspended_by': g.admin_user['id']
        })
        
        return jsonify({
            'message': 'User suspended successfully',
            'user_id': user_id,
            'reason': reason,
            'duration': duration
        })
        
    except Exception as e:
        logger.error(f"Error suspending user {user_id}: {str(e)}")
        return jsonify({'error': 'Failed to suspend user'}), 500

# System settings endpoints
@app.route('/settings', methods=['GET'])
@admin_required
@permission_required('system', 'read')
def get_settings():
    """Get system settings"""
    try:
        category = request.args.get('category')
        
        query = SystemSettings.query
        if category:
            query = query.filter_by(category=category)
        
        settings = query.all()
        
        # Group by category
        grouped_settings = {}
        for setting in settings:
            if setting.category not in grouped_settings:
                grouped_settings[setting.category] = {}
            grouped_settings[setting.category][setting.key] = setting.to_dict()
        
        log_action('view_settings', 'system')
        
        return jsonify(grouped_settings)
        
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        return jsonify({'error': 'Failed to get settings'}), 500

@app.route('/settings', methods=['POST'])
@admin_required
@permission_required('system', 'write')
def update_settings():
    """Update system settings"""
    try:
        data = request.get_json()
        
        updated_settings = []
        
        for category, settings in data.items():
            for key, value in settings.items():
                # Find existing setting or create new one
                setting = SystemSettings.query.filter_by(
                    category=category,
                    key=key
                ).first()
                
                old_value = setting.value if setting else None
                
                if setting:
                    setting.value = value
                    setting.updated_by = g.admin_user['id']
                    setting.updated_at = datetime.now(timezone.utc)
                else:
                    setting = SystemSettings(
                        category=category,
                        key=key,
                        value=value,
                        created_by=g.admin_user['id'],
                        updated_by=g.admin_user['id']
                    )
                    db.session.add(setting)
                
                updated_settings.append(setting.to_dict())
                
                log_action('update_setting', 'system', setting.id, old_value, value)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Settings updated successfully',
            'settings': updated_settings
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating settings: {str(e)}")
        return jsonify({'error': 'Failed to update settings'}), 500

# Audit log endpoints
@app.route('/audit-logs', methods=['GET'])
@admin_required
@permission_required('system', 'read')
def get_audit_logs():
    """Get audit logs"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 200)
        action = request.args.get('action')
        resource_type = request.args.get('resource_type')
        user_id = request.args.get('user_id')
        
        query = AuditLog.query
        
        if action:
            query = query.filter(AuditLog.action.ilike(f'%{action}%'))
        
        if resource_type:
            query = query.filter_by(resource_type=resource_type)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        logs = query.order_by(AuditLog.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'logs': [log.to_dict() for log in logs.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': logs.total,
                'pages': logs.pages
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting audit logs: {str(e)}")
        return jsonify({'error': 'Failed to get audit logs'}), 500

# Initialize database
@app.before_first_request
def create_tables():
    """Create database tables and default admin user"""
    try:
        db.create_all()
        
        # Create default admin user if not exists
        admin = AdminUser.query.filter_by(username='admin').first()
        if not admin:
            admin = AdminUser(
                username='admin',
                email='admin@odk.com',
                first_name='System',
                last_name='Administrator',
                role='super_admin',
                is_active=True,
                is_verified=True
            )
            admin.set_password('admin123')
            
            db.session.add(admin)
            db.session.commit()
            
            logger.info("Default admin user created: admin@odk.com / admin123")
        
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")

if __name__ == '__main__':
    port = int(os.getenv('ADMIN_SYSTEM_PORT', 5005))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Admin System service on port {port}")
    logger.info(f"Database type: {db_manager.config.database_type}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

