"""
Enhanced Authentication and Authorization System for ODK MCP System.
Provides 2FA, SSO, session management, and role-based access control.
"""

import os
import json
import uuid
import hashlib
import hmac
import secrets
import base64
import qrcode
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import pyotp
import bcrypt
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import sqlalchemy as sa
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, JSON, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from flask import Flask, request, jsonify, session, g
from flask_cors import CORS
import redis

from .config import AUTHENTICATION, ACCESS_CONTROL, AUDIT


# Database Models
Base = declarative_base()


class UserStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class SessionStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class AuditEventType(Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    TWO_FA_SETUP = "2fa_setup"
    TWO_FA_DISABLE = "2fa_disable"
    ROLE_CHANGE = "role_change"
    PERMISSION_CHANGE = "permission_change"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"


@dataclass
class AuthenticationResult:
    success: bool
    user_id: Optional[str] = None
    session_token: Optional[str] = None
    requires_2fa: bool = False
    error_message: Optional[str] = None
    lockout_remaining: Optional[int] = None


class User(Base):
    __tablename__ = 'auth_users'
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    
    # Profile information
    first_name = Column(String)
    last_name = Column(String)
    organization = Column(String)
    phone = Column(String)
    
    # Account status
    status = Column(String, default=UserStatus.ACTIVE.value)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    
    # Security settings
    role = Column(String, default="user")
    permissions = Column(JSON, default=list)
    
    # Password policy
    password_changed_at = Column(DateTime, default=datetime.utcnow)
    password_history = Column(JSON, default=list)
    force_password_change = Column(Boolean, default=False)
    
    # Account lockout
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    last_login_attempt = Column(DateTime)
    
    # Two-factor authentication
    two_fa_enabled = Column(Boolean, default=False)
    two_fa_secret = Column(String)
    two_fa_backup_codes = Column(JSON, default=list)
    two_fa_setup_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    last_activity_at = Column(DateTime)


class UserSession(Base):
    __tablename__ = 'auth_sessions'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    session_token = Column(String, unique=True, nullable=False)
    refresh_token = Column(String, unique=True)
    
    # Session details
    status = Column(String, default=SessionStatus.ACTIVE.value)
    ip_address = Column(String)
    user_agent = Column(Text)
    device_fingerprint = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Security flags
    is_trusted_device = Column(Boolean, default=False)
    requires_2fa_verification = Column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = 'auth_audit_logs'
    
    id = Column(String, primary_key=True)
    user_id = Column(String)
    session_id = Column(String)
    
    # Event details
    event_type = Column(String, nullable=False)
    event_description = Column(Text)
    event_data = Column(JSON)
    
    # Context
    ip_address = Column(String)
    user_agent = Column(Text)
    endpoint = Column(String)
    method = Column(String)
    
    # Risk assessment
    risk_score = Column(Integer, default=0)
    anomaly_detected = Column(Boolean, default=False)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow)


class APIKey(Base):
    __tablename__ = 'auth_api_keys'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    key_hash = Column(String, unique=True, nullable=False)
    key_prefix = Column(String, nullable=False)
    
    # Key details
    name = Column(String, nullable=False)
    description = Column(Text)
    permissions = Column(JSON, default=list)
    
    # Usage tracking
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0)
    
    # Status and expiry
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuthenticationManager:
    """
    Comprehensive authentication and authorization system.
    """
    
    def __init__(self, database_url: str = "sqlite:///auth.db", redis_url: str = None):
        """
        Initialize the authentication manager.
        
        Args:
            database_url: Database connection URL.
            redis_url: Redis connection URL for session storage.
        """
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Redis for session storage (optional)
        self.redis_client = None
        if redis_url:
            self.redis_client = redis.from_url(redis_url)
        
        # Encryption for sensitive data
        self.fernet = Fernet(self._derive_key(AUTHENTICATION["session_encryption_key"]))
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize Flask app
        self.app = Flask(__name__)
        self.app.secret_key = AUTHENTICATION["jwt_secret_key"]
        CORS(self.app)
        self._setup_routes()
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password."""
        password_bytes = password.encode()
        salt = b'salt_'  # In production, use a proper salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password_bytes))
    
    def _setup_routes(self):
        """Setup Flask routes for authentication."""
        
        @self.app.route('/api/auth/register', methods=['POST'])
        def register():
            """User registration endpoint."""
            try:
                data = request.get_json()
                result = self.register_user(
                    email=data.get('email'),
                    password=data.get('password'),
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'),
                    organization=data.get('organization')
                )
                
                if result['success']:
                    return jsonify({
                        "status": "success",
                        "message": "User registered successfully",
                        "user_id": result['user_id']
                    })
                else:
                    return jsonify({
                        "status": "error",
                        "message": result['error_message']
                    }), 400
                    
            except Exception as e:
                self.logger.error(f"Registration error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": "Registration failed"
                }), 500
        
        @self.app.route('/api/auth/login', methods=['POST'])
        def login():
            """User login endpoint."""
            try:
                data = request.get_json()
                ip_address = request.remote_addr
                user_agent = request.headers.get('User-Agent', '')
                
                result = self.authenticate_user(
                    email=data.get('email'),
                    password=data.get('password'),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    totp_code=data.get('totp_code')
                )
                
                if result.success:
                    response_data = {
                        "status": "success",
                        "message": "Login successful",
                        "session_token": result.session_token,
                        "requires_2fa": result.requires_2fa
                    }
                    
                    if not result.requires_2fa:
                        response_data["user"] = self.get_user_profile(result.user_id)
                    
                    return jsonify(response_data)
                else:
                    return jsonify({
                        "status": "error",
                        "message": result.error_message,
                        "lockout_remaining": result.lockout_remaining
                    }), 401
                    
            except Exception as e:
                self.logger.error(f"Login error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": "Login failed"
                }), 500
        
        @self.app.route('/api/auth/logout', methods=['POST'])
        def logout():
            """User logout endpoint."""
            try:
                session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
                
                if session_token:
                    self.revoke_session(session_token)
                
                return jsonify({
                    "status": "success",
                    "message": "Logged out successfully"
                })
                
            except Exception as e:
                self.logger.error(f"Logout error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": "Logout failed"
                }), 500
        
        @self.app.route('/api/auth/2fa/setup', methods=['POST'])
        def setup_2fa():
            """Setup two-factor authentication."""
            try:
                session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
                user_id = self.validate_session(session_token)
                
                if not user_id:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid session"
                    }), 401
                
                result = self.setup_two_factor_auth(user_id)
                
                return jsonify({
                    "status": "success",
                    "qr_code_url": result["qr_code_url"],
                    "backup_codes": result["backup_codes"],
                    "secret": result["secret"]
                })
                
            except Exception as e:
                self.logger.error(f"2FA setup error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": "2FA setup failed"
                }), 500
        
        @self.app.route('/api/auth/2fa/verify', methods=['POST'])
        def verify_2fa():
            """Verify two-factor authentication setup."""
            try:
                session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
                user_id = self.validate_session(session_token)
                
                if not user_id:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid session"
                    }), 401
                
                data = request.get_json()
                totp_code = data.get('totp_code')
                
                if self.verify_totp_code(user_id, totp_code):
                    self.enable_two_factor_auth(user_id)
                    
                    return jsonify({
                        "status": "success",
                        "message": "2FA enabled successfully"
                    })
                else:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid verification code"
                    }), 400
                    
            except Exception as e:
                self.logger.error(f"2FA verification error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": "2FA verification failed"
                }), 500
        
        @self.app.route('/api/auth/profile')
        def get_profile():
            """Get user profile."""
            try:
                session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
                user_id = self.validate_session(session_token)
                
                if not user_id:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid session"
                    }), 401
                
                profile = self.get_user_profile(user_id)
                
                return jsonify({
                    "status": "success",
                    "profile": profile
                })
                
            except Exception as e:
                self.logger.error(f"Profile error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": "Failed to get profile"
                }), 500
        
        @self.app.route('/api/auth/change-password', methods=['POST'])
        def change_password():
            """Change user password."""
            try:
                session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
                user_id = self.validate_session(session_token)
                
                if not user_id:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid session"
                    }), 401
                
                data = request.get_json()
                current_password = data.get('current_password')
                new_password = data.get('new_password')
                
                result = self.change_password(user_id, current_password, new_password)
                
                if result['success']:
                    return jsonify({
                        "status": "success",
                        "message": "Password changed successfully"
                    })
                else:
                    return jsonify({
                        "status": "error",
                        "message": result['error_message']
                    }), 400
                    
            except Exception as e:
                self.logger.error(f"Password change error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": "Password change failed"
                }), 500
        
        @self.app.route('/api/auth/api-keys', methods=['GET'])
        def get_api_keys():
            """Get user's API keys."""
            try:
                session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
                user_id = self.validate_session(session_token)
                
                if not user_id:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid session"
                    }), 401
                
                api_keys = self.get_user_api_keys(user_id)
                
                return jsonify({
                    "status": "success",
                    "api_keys": api_keys
                })
                
            except Exception as e:
                self.logger.error(f"API keys error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": "Failed to get API keys"
                }), 500
        
        @self.app.route('/api/auth/api-keys', methods=['POST'])
        def create_api_key():
            """Create new API key."""
            try:
                session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
                user_id = self.validate_session(session_token)
                
                if not user_id:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid session"
                    }), 401
                
                data = request.get_json()
                name = data.get('name')
                description = data.get('description', '')
                permissions = data.get('permissions', [])
                expires_in_days = data.get('expires_in_days', 365)
                
                api_key = self.create_api_key(user_id, name, description, permissions, expires_in_days)
                
                return jsonify({
                    "status": "success",
                    "api_key": api_key
                })
                
            except Exception as e:
                self.logger.error(f"API key creation error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": "Failed to create API key"
                }), 500
    
    def register_user(
        self,
        email: str,
        password: str,
        first_name: str = None,
        last_name: str = None,
        organization: str = None
    ) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            email: User email address.
            password: User password.
            first_name: User first name.
            last_name: User last name.
            organization: User organization.
            
        Returns:
            Registration result dictionary.
        """
        try:
            with self.SessionLocal() as db:
                # Check if user already exists
                existing_user = db.query(User).filter(User.email == email).first()
                if existing_user:
                    return {
                        "success": False,
                        "error_message": "User with this email already exists"
                    }
                
                # Validate password
                if not self._validate_password(password):
                    return {
                        "success": False,
                        "error_message": "Password does not meet security requirements"
                    }
                
                # Create user
                user_id = str(uuid.uuid4())
                salt = secrets.token_hex(16)
                password_hash = self._hash_password(password, salt)
                
                user = User(
                    id=user_id,
                    email=email,
                    password_hash=password_hash,
                    salt=salt,
                    first_name=first_name,
                    last_name=last_name,
                    organization=organization,
                    status=UserStatus.PENDING_VERIFICATION.value
                )
                
                db.add(user)
                db.commit()
                
                # Log registration
                self._log_audit_event(
                    user_id=user_id,
                    event_type=AuditEventType.LOGIN_SUCCESS.value,
                    event_description="User registered",
                    ip_address=request.remote_addr if request else None
                )
                
                return {
                    "success": True,
                    "user_id": user_id
                }
                
        except Exception as e:
            self.logger.error(f"Registration error: {str(e)}")
            return {
                "success": False,
                "error_message": "Registration failed"
            }
    
    def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None,
        totp_code: str = None
    ) -> AuthenticationResult:
        """
        Authenticate a user.
        
        Args:
            email: User email address.
            password: User password.
            ip_address: Client IP address.
            user_agent: Client user agent.
            totp_code: TOTP code for 2FA.
            
        Returns:
            Authentication result.
        """
        try:
            with self.SessionLocal() as db:
                user = db.query(User).filter(User.email == email).first()
                
                if not user:
                    self._log_audit_event(
                        event_type=AuditEventType.LOGIN_FAILURE.value,
                        event_description=f"Login attempt with non-existent email: {email}",
                        ip_address=ip_address
                    )
                    return AuthenticationResult(
                        success=False,
                        error_message="Invalid credentials"
                    )
                
                # Check account status
                if user.status != UserStatus.ACTIVE.value:
                    return AuthenticationResult(
                        success=False,
                        error_message=f"Account is {user.status}"
                    )
                
                # Check account lockout
                if user.locked_until and user.locked_until > datetime.utcnow():
                    remaining_seconds = int((user.locked_until - datetime.utcnow()).total_seconds())
                    return AuthenticationResult(
                        success=False,
                        error_message="Account is locked",
                        lockout_remaining=remaining_seconds
                    )
                
                # Verify password
                if not self._verify_password(password, user.password_hash, user.salt):
                    user.failed_login_attempts += 1
                    user.last_login_attempt = datetime.utcnow()
                    
                    # Check for account lockout
                    if user.failed_login_attempts >= AUTHENTICATION["max_login_attempts"]:
                        lockout_duration = timedelta(minutes=AUTHENTICATION["lockout_duration_minutes"])
                        user.locked_until = datetime.utcnow() + lockout_duration
                        
                        self._log_audit_event(
                            user_id=user.id,
                            event_type=AuditEventType.ACCOUNT_LOCKED.value,
                            event_description="Account locked due to failed login attempts",
                            ip_address=ip_address
                        )
                    
                    db.commit()
                    
                    self._log_audit_event(
                        user_id=user.id,
                        event_type=AuditEventType.LOGIN_FAILURE.value,
                        event_description="Invalid password",
                        ip_address=ip_address
                    )
                    
                    return AuthenticationResult(
                        success=False,
                        error_message="Invalid credentials"
                    )
                
                # Check 2FA if enabled
                if user.two_fa_enabled:
                    if not totp_code:
                        return AuthenticationResult(
                            success=False,
                            requires_2fa=True,
                            user_id=user.id,
                            error_message="2FA code required"
                        )
                    
                    if not self.verify_totp_code(user.id, totp_code):
                        user.failed_login_attempts += 1
                        db.commit()
                        
                        return AuthenticationResult(
                            success=False,
                            error_message="Invalid 2FA code"
                        )
                
                # Reset failed attempts on successful login
                user.failed_login_attempts = 0
                user.locked_until = None
                user.last_login_at = datetime.utcnow()
                user.last_activity_at = datetime.utcnow()
                
                # Create session
                session_token = self._create_session(user.id, ip_address, user_agent)
                
                db.commit()
                
                self._log_audit_event(
                    user_id=user.id,
                    event_type=AuditEventType.LOGIN_SUCCESS.value,
                    event_description="Successful login",
                    ip_address=ip_address
                )
                
                return AuthenticationResult(
                    success=True,
                    user_id=user.id,
                    session_token=session_token
                )
                
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            return AuthenticationResult(
                success=False,
                error_message="Authentication failed"
            )
    
    def setup_two_factor_auth(self, user_id: str) -> Dict[str, Any]:
        """
        Setup two-factor authentication for a user.
        
        Args:
            user_id: User ID.
            
        Returns:
            2FA setup details including QR code and backup codes.
        """
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise ValueError("User not found")
            
            # Generate TOTP secret
            secret = pyotp.random_base32()
            
            # Generate backup codes
            backup_codes = [secrets.token_hex(4).upper() for _ in range(AUTHENTICATION["2fa_backup_codes_count"])]
            
            # Create TOTP URI for QR code
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user.email,
                issuer_name=AUTHENTICATION["2fa_issuer"]
            )
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(totp_uri)
            qr.make(fit=True)
            
            # Save to user (but don't enable yet)
            user.two_fa_secret = secret
            user.two_fa_backup_codes = backup_codes
            
            db.commit()
            
            return {
                "secret": secret,
                "qr_code_url": totp_uri,
                "backup_codes": backup_codes
            }
    
    def verify_totp_code(self, user_id: str, totp_code: str) -> bool:
        """
        Verify TOTP code for a user.
        
        Args:
            user_id: User ID.
            totp_code: TOTP code to verify.
            
        Returns:
            True if code is valid, False otherwise.
        """
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user or not user.two_fa_secret:
                return False
            
            # Check TOTP code
            totp = pyotp.TOTP(user.two_fa_secret)
            if totp.verify(totp_code, valid_window=1):
                return True
            
            # Check backup codes
            if totp_code.upper() in user.two_fa_backup_codes:
                # Remove used backup code
                user.two_fa_backup_codes.remove(totp_code.upper())
                db.commit()
                return True
            
            return False
    
    def enable_two_factor_auth(self, user_id: str) -> None:
        """Enable two-factor authentication for a user."""
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            
            if user:
                user.two_fa_enabled = True
                user.two_fa_setup_at = datetime.utcnow()
                db.commit()
                
                self._log_audit_event(
                    user_id=user_id,
                    event_type=AuditEventType.TWO_FA_SETUP.value,
                    event_description="Two-factor authentication enabled"
                )
    
    def _create_session(self, user_id: str, ip_address: str = None, user_agent: str = None) -> str:
        """Create a new user session."""
        with self.SessionLocal() as db:
            session_id = str(uuid.uuid4())
            session_token = secrets.token_urlsafe(32)
            refresh_token = secrets.token_urlsafe(32)
            
            expires_at = datetime.utcnow() + timedelta(hours=AUTHENTICATION["jwt_expiration_hours"])
            
            session = UserSession(
                id=session_id,
                user_id=user_id,
                session_token=session_token,
                refresh_token=refresh_token,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at
            )
            
            db.add(session)
            db.commit()
            
            return session_token
    
    def validate_session(self, session_token: str) -> Optional[str]:
        """
        Validate a session token.
        
        Args:
            session_token: Session token to validate.
            
        Returns:
            User ID if session is valid, None otherwise.
        """
        try:
            with self.SessionLocal() as db:
                session = db.query(UserSession).filter(
                    UserSession.session_token == session_token,
                    UserSession.status == SessionStatus.ACTIVE.value,
                    UserSession.expires_at > datetime.utcnow()
                ).first()
                
                if session:
                    # Update last activity
                    session.last_activity_at = datetime.utcnow()
                    db.commit()
                    
                    return session.user_id
                
                return None
                
        except Exception as e:
            self.logger.error(f"Session validation error: {str(e)}")
            return None
    
    def revoke_session(self, session_token: str) -> None:
        """Revoke a user session."""
        with self.SessionLocal() as db:
            session = db.query(UserSession).filter(
                UserSession.session_token == session_token
            ).first()
            
            if session:
                session.status = SessionStatus.REVOKED.value
                db.commit()
                
                self._log_audit_event(
                    user_id=session.user_id,
                    session_id=session.id,
                    event_type=AuditEventType.LOGOUT.value,
                    event_description="Session revoked"
                )
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile information."""
        with self.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            
            if user:
                return {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "organization": user.organization,
                    "role": user.role,
                    "permissions": user.permissions,
                    "two_fa_enabled": user.two_fa_enabled,
                    "email_verified": user.email_verified,
                    "created_at": user.created_at.isoformat(),
                    "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
                }
            
            return None
    
    def change_password(self, user_id: str, current_password: str, new_password: str) -> Dict[str, Any]:
        """Change user password."""
        try:
            with self.SessionLocal() as db:
                user = db.query(User).filter(User.id == user_id).first()
                
                if not user:
                    return {
                        "success": False,
                        "error_message": "User not found"
                    }
                
                # Verify current password
                if not self._verify_password(current_password, user.password_hash, user.salt):
                    return {
                        "success": False,
                        "error_message": "Current password is incorrect"
                    }
                
                # Validate new password
                if not self._validate_password(new_password):
                    return {
                        "success": False,
                        "error_message": "New password does not meet security requirements"
                    }
                
                # Check password history
                new_password_hash = self._hash_password(new_password, user.salt)
                if new_password_hash in user.password_history:
                    return {
                        "success": False,
                        "error_message": "Cannot reuse a recent password"
                    }
                
                # Update password
                user.password_hash = new_password_hash
                user.password_changed_at = datetime.utcnow()
                user.force_password_change = False
                
                # Update password history
                password_history = user.password_history or []
                password_history.append(user.password_hash)
                if len(password_history) > AUTHENTICATION["password_history_count"]:
                    password_history = password_history[-AUTHENTICATION["password_history_count"]:]
                user.password_history = password_history
                
                db.commit()
                
                self._log_audit_event(
                    user_id=user_id,
                    event_type=AuditEventType.PASSWORD_CHANGE.value,
                    event_description="Password changed"
                )
                
                return {
                    "success": True
                }
                
        except Exception as e:
            self.logger.error(f"Password change error: {str(e)}")
            return {
                "success": False,
                "error_message": "Password change failed"
            }
    
    def create_api_key(
        self,
        user_id: str,
        name: str,
        description: str = "",
        permissions: List[str] = None,
        expires_in_days: int = 365
    ) -> Dict[str, Any]:
        """Create a new API key for a user."""
        with self.SessionLocal() as db:
            # Generate API key
            api_key = f"odk_{secrets.token_urlsafe(32)}"
            key_prefix = api_key[:12]
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            api_key_record = APIKey(
                id=str(uuid.uuid4()),
                user_id=user_id,
                key_hash=key_hash,
                key_prefix=key_prefix,
                name=name,
                description=description,
                permissions=permissions or [],
                expires_at=expires_at
            )
            
            db.add(api_key_record)
            db.commit()
            
            return {
                "id": api_key_record.id,
                "key": api_key,  # Only returned once
                "name": name,
                "description": description,
                "permissions": permissions or [],
                "expires_at": expires_at.isoformat()
            }
    
    def get_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's API keys (without the actual key values)."""
        with self.SessionLocal() as db:
            api_keys = db.query(APIKey).filter(
                APIKey.user_id == user_id,
                APIKey.is_active == True
            ).all()
            
            return [
                {
                    "id": key.id,
                    "name": key.name,
                    "description": key.description,
                    "key_prefix": key.key_prefix,
                    "permissions": key.permissions,
                    "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                    "usage_count": key.usage_count,
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                    "created_at": key.created_at.isoformat()
                }
                for key in api_keys
            ]
    
    def _validate_password(self, password: str) -> bool:
        """Validate password against security policy."""
        if len(password) < AUTHENTICATION["password_min_length"]:
            return False
        
        if AUTHENTICATION["password_require_uppercase"] and not any(c.isupper() for c in password):
            return False
        
        if AUTHENTICATION["password_require_lowercase"] and not any(c.islower() for c in password):
            return False
        
        if AUTHENTICATION["password_require_numbers"] and not any(c.isdigit() for c in password):
            return False
        
        if AUTHENTICATION["password_require_special_chars"] and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False
        
        return True
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt."""
        return bcrypt.hashpw((password + salt).encode(), bcrypt.gensalt()).decode()
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw((password + salt).encode(), password_hash.encode())
    
    def _log_audit_event(
        self,
        event_type: str,
        event_description: str,
        user_id: str = None,
        session_id: str = None,
        ip_address: str = None,
        event_data: Dict[str, Any] = None
    ) -> None:
        """Log an audit event."""
        try:
            with self.SessionLocal() as db:
                audit_log = AuditLog(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    session_id=session_id,
                    event_type=event_type,
                    event_description=event_description,
                    event_data=event_data,
                    ip_address=ip_address,
                    user_agent=request.headers.get('User-Agent') if request else None,
                    endpoint=request.endpoint if request else None,
                    method=request.method if request else None
                )
                
                db.add(audit_log)
                db.commit()
                
        except Exception as e:
            self.logger.error(f"Audit logging error: {str(e)}")
    
    def run(self, host='0.0.0.0', port=5002, debug=False):
        """Run the authentication application."""
        self.app.run(host=host, port=port, debug=debug)


# Create a global instance
auth_manager = AuthenticationManager()

