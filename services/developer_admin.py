"""
Developer-Only Admin System
Comprehensive administrative interface for system developers only
"""

import os
import json
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from flask import Flask, request, jsonify, session, abort
from flask_cors import CORS
from functools import wraps
import jwt
from cryptography.fernet import Fernet
import subprocess
import psutil
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdminPermission(Enum):
    """Admin permission levels"""
    SUPER_ADMIN = "super_admin"  # Full system access
    SYSTEM_ADMIN = "system_admin"  # System monitoring and maintenance
    DATABASE_ADMIN = "database_admin"  # Database operations
    USER_ADMIN = "user_admin"  # User management
    SECURITY_ADMIN = "security_admin"  # Security and audit operations

class SystemStatus(Enum):
    """System status indicators"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    MAINTENANCE = "maintenance"

@dataclass
class AdminUser:
    """Developer admin user"""
    id: str
    username: str
    email: str
    permissions: List[AdminPermission]
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool
    mfa_enabled: bool
    api_key: Optional[str]

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    database_connections: int
    active_users: int
    api_requests_per_minute: int
    error_rate: float

class DeveloperAdminSystem:
    """
    Comprehensive developer-only admin system
    """
    
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = os.getenv('ADMIN_SECRET_KEY', secrets.token_hex(32))
        CORS(self.app, origins=['http://localhost:3000', 'http://localhost:5000'])
        
        # Database connections
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'odk_mcp_system'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres')
        }
        
        # Redis connection
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=0,
            decode_responses=True
        )
        
        # Encryption for sensitive data
        self.cipher_suite = Fernet(self._get_or_create_encryption_key())
        
        # Initialize admin users
        self.initialize_admin_users()
        
        # Setup routes
        self.setup_routes()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for admin system"""
        key_file = '/tmp/admin_encryption.key'
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def initialize_admin_users(self):
        """Initialize default admin users"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Create admin users table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id VARCHAR(50) PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    permissions TEXT[] NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    mfa_enabled BOOLEAN DEFAULT FALSE,
                    api_key VARCHAR(255),
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP
                )
            """)
            
            # Create default super admin if not exists
            admin_id = "admin_001"
            admin_password = "DevAdmin@2024!"  # Should be changed immediately
            password_hash = hashlib.pbkdf2_hmac('sha256', 
                                              admin_password.encode('utf-8'), 
                                              b'salt_', 100000).hex()
            
            cursor.execute("""
                INSERT INTO admin_users (id, username, email, password_hash, permissions)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
            """, (
                admin_id,
                'developer_admin',
                'admin@odk-system.dev',
                password_hash,
                [perm.value for perm in AdminPermission]
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("Admin users initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing admin users: {e}")
    
    def authenticate_admin(self, username: str, password: str) -> Optional[AdminUser]:
        """Authenticate admin user"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Check if account is locked
            cursor.execute("""
                SELECT * FROM admin_users 
                WHERE username = %s AND is_active = TRUE
            """, (username,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                return None
            
            # Check if account is locked
            if user_data['locked_until'] and user_data['locked_until'] > datetime.now():
                logger.warning(f"Admin account {username} is locked")
                return None
            
            # Verify password
            password_hash = hashlib.pbkdf2_hmac('sha256', 
                                              password.encode('utf-8'), 
                                              b'salt_', 100000).hex()
            
            if user_data['password_hash'] != password_hash:
                # Increment login attempts
                cursor.execute("""
                    UPDATE admin_users 
                    SET login_attempts = login_attempts + 1,
                        locked_until = CASE 
                            WHEN login_attempts >= 4 THEN CURRENT_TIMESTAMP + INTERVAL '30 minutes'
                            ELSE locked_until
                        END
                    WHERE username = %s
                """, (username,))
                conn.commit()
                return None
            
            # Reset login attempts and update last login
            cursor.execute("""
                UPDATE admin_users 
                SET login_attempts = 0, last_login = CURRENT_TIMESTAMP, locked_until = NULL
                WHERE username = %s
            """, (username,))
            conn.commit()
            
            # Create AdminUser object
            admin_user = AdminUser(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                permissions=[AdminPermission(perm) for perm in user_data['permissions']],
                created_at=user_data['created_at'],
                last_login=user_data['last_login'],
                is_active=user_data['is_active'],
                mfa_enabled=user_data['mfa_enabled'],
                api_key=user_data['api_key']
            )
            
            cursor.close()
            conn.close()
            
            return admin_user
            
        except Exception as e:
            logger.error(f"Error authenticating admin: {e}")
            return None
    
    def require_admin_permission(self, required_permission: AdminPermission):
        """Decorator to require specific admin permission"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Check if user is authenticated
                if 'admin_user_id' not in session:
                    abort(401, description="Admin authentication required")
                
                # Get admin user
                admin_user = self.get_admin_user(session['admin_user_id'])
                if not admin_user or not admin_user.is_active:
                    abort(401, description="Invalid admin session")
                
                # Check permission
                if (required_permission not in admin_user.permissions and 
                    AdminPermission.SUPER_ADMIN not in admin_user.permissions):
                    abort(403, description="Insufficient admin permissions")
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    def get_admin_user(self, user_id: str) -> Optional[AdminUser]:
        """Get admin user by ID"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM admin_users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                return AdminUser(
                    id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    permissions=[AdminPermission(perm) for perm in user_data['permissions']],
                    created_at=user_data['created_at'],
                    last_login=user_data['last_login'],
                    is_active=user_data['is_active'],
                    mfa_enabled=user_data['mfa_enabled'],
                    api_key=user_data['api_key']
                )
            
            cursor.close()
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Error getting admin user: {e}")
            return None
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system performance metrics"""
        try:
            # CPU and Memory usage
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Database connections
            db_connections = self.get_database_connection_count()
            
            # Active users (from Redis sessions)
            active_users = len(self.redis_client.keys('session:*'))
            
            # API requests per minute (from Redis metrics)
            api_requests = int(self.redis_client.get('api_requests_per_minute') or 0)
            
            # Error rate (from Redis metrics)
            error_rate = float(self.redis_client.get('error_rate') or 0.0)
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=(disk.used / disk.total) * 100,
                database_connections=db_connections,
                active_users=active_users,
                api_requests_per_minute=api_requests,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                database_connections=0,
                active_users=0,
                api_requests_per_minute=0,
                error_rate=0.0
            )
    
    def get_database_connection_count(self) -> int:
        """Get current database connection count"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT count(*) 
                FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting database connections: {e}")
            return 0
    
    def get_system_status(self) -> SystemStatus:
        """Determine overall system status"""
        metrics = self.get_system_metrics()
        
        # Critical thresholds
        if (metrics.cpu_usage > 90 or 
            metrics.memory_usage > 95 or 
            metrics.disk_usage > 95 or
            metrics.error_rate > 0.1):
            return SystemStatus.CRITICAL
        
        # Warning thresholds
        if (metrics.cpu_usage > 70 or 
            metrics.memory_usage > 80 or 
            metrics.disk_usage > 80 or
            metrics.error_rate > 0.05):
            return SystemStatus.WARNING
        
        return SystemStatus.HEALTHY
    
    def setup_routes(self):
        """Setup admin API routes"""
        
        @self.app.route('/admin/login', methods=['POST'])
        def admin_login():
            """Admin login endpoint"""
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return jsonify({'error': 'Username and password required'}), 400
            
            admin_user = self.authenticate_admin(username, password)
            
            if admin_user:
                session['admin_user_id'] = admin_user.id
                session['admin_username'] = admin_user.username
                
                return jsonify({
                    'success': True,
                    'user': {
                        'id': admin_user.id,
                        'username': admin_user.username,
                        'email': admin_user.email,
                        'permissions': [perm.value for perm in admin_user.permissions]
                    }
                })
            else:
                return jsonify({'error': 'Invalid credentials'}), 401
        
        @self.app.route('/admin/logout', methods=['POST'])
        def admin_logout():
            """Admin logout endpoint"""
            session.clear()
            return jsonify({'success': True})
        
        @self.app.route('/admin/dashboard', methods=['GET'])
        @self.require_admin_permission(AdminPermission.SYSTEM_ADMIN)
        def admin_dashboard():
            """Admin dashboard with system overview"""
            metrics = self.get_system_metrics()
            status = self.get_system_status()
            
            return jsonify({
                'system_status': status.value,
                'metrics': asdict(metrics),
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/admin/users', methods=['GET'])
        @self.require_admin_permission(AdminPermission.USER_ADMIN)
        def list_users():
            """List all system users"""
            try:
                conn = psycopg2.connect(**self.db_config)
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute("""
                    SELECT id, username, email, created_at, last_login, is_active
                    FROM users 
                    ORDER BY created_at DESC
                    LIMIT 100
                """)
                
                users = cursor.fetchall()
                cursor.close()
                conn.close()
                
                return jsonify({
                    'users': [dict(user) for user in users],
                    'total_count': len(users)
                })
                
            except Exception as e:
                logger.error(f"Error listing users: {e}")
                return jsonify({'error': 'Failed to retrieve users'}), 500
        
        @self.app.route('/admin/users/<user_id>/suspend', methods=['POST'])
        @self.require_admin_permission(AdminPermission.USER_ADMIN)
        def suspend_user(user_id):
            """Suspend a user account"""
            try:
                conn = psycopg2.connect(**self.db_config)
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE users 
                    SET is_active = FALSE, suspended_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (user_id,))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                # Log admin action
                logger.info(f"User {user_id} suspended by admin {session['admin_username']}")
                
                return jsonify({'success': True})
                
            except Exception as e:
                logger.error(f"Error suspending user: {e}")
                return jsonify({'error': 'Failed to suspend user'}), 500
        
        @self.app.route('/admin/database/stats', methods=['GET'])
        @self.require_admin_permission(AdminPermission.DATABASE_ADMIN)
        def database_stats():
            """Get database statistics"""
            try:
                conn = psycopg2.connect(**self.db_config)
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                # Table sizes
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY size_bytes DESC
                """)
                
                table_sizes = cursor.fetchall()
                
                # Database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as database_size
                """)
                
                db_size = cursor.fetchone()['database_size']
                
                # Connection stats
                cursor.execute("""
                    SELECT 
                        state,
                        count(*) as count
                    FROM pg_stat_activity 
                    GROUP BY state
                """)
                
                connection_stats = cursor.fetchall()
                
                cursor.close()
                conn.close()
                
                return jsonify({
                    'database_size': db_size,
                    'table_sizes': [dict(table) for table in table_sizes],
                    'connection_stats': [dict(stat) for stat in connection_stats]
                })
                
            except Exception as e:
                logger.error(f"Error getting database stats: {e}")
                return jsonify({'error': 'Failed to retrieve database statistics'}), 500
        
        @self.app.route('/admin/security/audit-log', methods=['GET'])
        @self.require_admin_permission(AdminPermission.SECURITY_ADMIN)
        def security_audit_log():
            """Get security audit log"""
            try:
                conn = psycopg2.connect(**self.db_config)
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute("""
                    SELECT 
                        timestamp,
                        user_id,
                        action,
                        resource,
                        ip_address,
                        user_agent,
                        success
                    FROM audit_log 
                    ORDER BY timestamp DESC
                    LIMIT 100
                """)
                
                audit_entries = cursor.fetchall()
                cursor.close()
                conn.close()
                
                return jsonify({
                    'audit_log': [dict(entry) for entry in audit_entries]
                })
                
            except Exception as e:
                logger.error(f"Error getting audit log: {e}")
                return jsonify({'error': 'Failed to retrieve audit log'}), 500
        
        @self.app.route('/admin/system/backup', methods=['POST'])
        @self.require_admin_permission(AdminPermission.SUPER_ADMIN)
        def create_system_backup():
            """Create system backup"""
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = f"/tmp/odk_backup_{timestamp}.sql"
                
                # Create database backup
                subprocess.run([
                    'pg_dump',
                    '-h', self.db_config['host'],
                    '-p', self.db_config['port'],
                    '-U', self.db_config['user'],
                    '-d', self.db_config['database'],
                    '-f', backup_file
                ], check=True, env={'PGPASSWORD': self.db_config['password']})
                
                # Log backup creation
                logger.info(f"System backup created: {backup_file} by admin {session['admin_username']}")
                
                return jsonify({
                    'success': True,
                    'backup_file': backup_file,
                    'timestamp': timestamp
                })
                
            except Exception as e:
                logger.error(f"Error creating backup: {e}")
                return jsonify({'error': 'Failed to create backup'}), 500
        
        @self.app.route('/admin/system/maintenance', methods=['POST'])
        @self.require_admin_permission(AdminPermission.SUPER_ADMIN)
        def toggle_maintenance_mode():
            """Toggle system maintenance mode"""
            data = request.get_json()
            maintenance_mode = data.get('enabled', False)
            
            try:
                # Set maintenance mode in Redis
                self.redis_client.set('maintenance_mode', str(maintenance_mode))
                
                if maintenance_mode:
                    message = data.get('message', 'System is under maintenance')
                    self.redis_client.set('maintenance_message', message)
                
                logger.info(f"Maintenance mode {'enabled' if maintenance_mode else 'disabled'} by admin {session['admin_username']}")
                
                return jsonify({
                    'success': True,
                    'maintenance_mode': maintenance_mode
                })
                
            except Exception as e:
                logger.error(f"Error toggling maintenance mode: {e}")
                return jsonify({'error': 'Failed to toggle maintenance mode'}), 500
    
    def run(self, host='0.0.0.0', port=5555, debug=False):
        """Run the admin system"""
        logger.info("Starting Developer Admin System")
        logger.info("=" * 50)
        logger.info("🔐 DEVELOPER ADMIN SYSTEM")
        logger.info("=" * 50)
        logger.info("Default Admin Credentials:")
        logger.info("Username: developer_admin")
        logger.info("Password: DevAdmin@2024!")
        logger.info("⚠️  CHANGE PASSWORD IMMEDIATELY AFTER FIRST LOGIN")
        logger.info("=" * 50)
        logger.info(f"Admin Interface: http://{host}:{port}/admin/dashboard")
        logger.info("=" * 50)
        
        self.app.run(host=host, port=port, debug=debug)

# Example usage
if __name__ == '__main__':
    admin_system = DeveloperAdminSystem()
    admin_system.run(debug=True)

