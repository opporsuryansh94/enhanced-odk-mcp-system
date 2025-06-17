"""
Enhanced API Gateway for ODK MCP System.
Provides unified API access, rate limiting, authentication, and webhook management.
"""

import os
import json
import uuid
import time
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import asyncio
import aiohttp

from flask import Flask, request, jsonify, g, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import requests
from werkzeug.exceptions import TooManyRequests, Unauthorized, Forbidden
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database Models
Base = declarative_base()


class APIKeyStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"
    EXPIRED = "expired"


class WebhookStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"


class IntegrationType(Enum):
    WEBHOOK = "webhook"
    API_CONNECTOR = "api_connector"
    DATA_SYNC = "data_sync"
    NOTIFICATION = "notification"


@dataclass
class APIResponse:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    status_code: int = 200


class APIKey(Base):
    __tablename__ = 'api_keys'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    key_hash = Column(String, unique=True, nullable=False)
    key_prefix = Column(String, nullable=False)
    
    # Key details
    name = Column(String, nullable=False)
    description = Column(Text)
    permissions = Column(JSON, default=list)
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=1000)
    rate_limit_per_day = Column(Integer, default=10000)
    
    # Usage tracking
    total_requests = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    
    # Status and expiry
    status = Column(String, default=APIKeyStatus.ACTIVE.value)
    expires_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Webhook(Base):
    __tablename__ = 'webhooks'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    
    # Webhook details
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    secret = Column(String)
    
    # Event configuration
    events = Column(JSON, default=list)
    filters = Column(JSON, default=dict)
    
    # Delivery settings
    retry_count = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=30)
    
    # Status and statistics
    status = Column(String, default=WebhookStatus.ACTIVE.value)
    total_deliveries = Column(Integer, default=0)
    successful_deliveries = Column(Integer, default=0)
    failed_deliveries = Column(Integer, default=0)
    last_delivery_at = Column(DateTime)
    last_success_at = Column(DateTime)
    last_failure_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebhookDelivery(Base):
    __tablename__ = 'webhook_deliveries'
    
    id = Column(String, primary_key=True)
    webhook_id = Column(String, nullable=False)
    
    # Delivery details
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    
    # Request details
    request_headers = Column(JSON)
    request_body = Column(Text)
    
    # Response details
    response_status = Column(Integer)
    response_headers = Column(JSON)
    response_body = Column(Text)
    
    # Timing
    delivery_duration_ms = Column(Integer)
    
    # Status
    success = Column(Boolean, default=False)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime)


class Integration(Base):
    __tablename__ = 'integrations'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    
    # Integration details
    name = Column(String, nullable=False)
    integration_type = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # slack, teams, zapier, etc.
    
    # Configuration
    config = Column(JSON, nullable=False)
    credentials = Column(JSON)  # Encrypted
    
    # Mapping and transformation
    field_mapping = Column(JSON, default=dict)
    data_transformation = Column(JSON, default=dict)
    
    # Status and settings
    is_active = Column(Boolean, default=True)
    auto_sync = Column(Boolean, default=False)
    sync_frequency_minutes = Column(Integer, default=60)
    
    # Statistics
    total_syncs = Column(Integer, default=0)
    successful_syncs = Column(Integer, default=0)
    failed_syncs = Column(Integer, default=0)
    last_sync_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class APIGateway:
    """
    Comprehensive API Gateway with rate limiting, authentication, and webhook management.
    """
    
    def __init__(self, database_url: str = "sqlite:///api_gateway.db", redis_url: str = None):
        """
        Initialize the API Gateway.
        
        Args:
            database_url: Database connection URL.
            redis_url: Redis connection URL for rate limiting.
        """
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Redis for rate limiting
        self.redis_client = None
        if redis_url:
            self.redis_client = redis.from_url(redis_url)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize Flask app
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Setup rate limiter
        self.limiter = Limiter(
            app=self.app,
            key_func=self._get_rate_limit_key,
            storage_uri=redis_url or "memory://",
            default_limits=["1000 per hour", "100 per minute"]
        )
        
        # Webhook delivery queue
        self.webhook_queue = []
        
        self._setup_routes()
        self._setup_error_handlers()
    
    def _get_rate_limit_key(self):
        """Get rate limiting key based on API key or IP address."""
        api_key = request.headers.get('X-API-Key')
        if api_key:
            return f"api_key:{api_key}"
        return get_remote_address()
    
    def _setup_routes(self):
        """Setup API Gateway routes."""
        
        # API Key Management
        @self.app.route('/api/gateway/keys', methods=['GET'])
        @self.require_auth
        def get_api_keys():
            """Get user's API keys."""
            try:
                user_id = g.current_user_id
                
                with self.SessionLocal() as db:
                    keys = db.query(APIKey).filter(
                        APIKey.user_id == user_id,
                        APIKey.status != APIKeyStatus.REVOKED.value
                    ).all()
                    
                    key_list = []
                    for key in keys:
                        key_list.append({
                            "id": key.id,
                            "name": key.name,
                            "description": key.description,
                            "key_prefix": key.key_prefix,
                            "permissions": key.permissions,
                            "rate_limits": {
                                "per_minute": key.rate_limit_per_minute,
                                "per_hour": key.rate_limit_per_hour,
                                "per_day": key.rate_limit_per_day
                            },
                            "usage": {
                                "total_requests": key.total_requests,
                                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None
                            },
                            "status": key.status,
                            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                            "created_at": key.created_at.isoformat()
                        })
                    
                    return jsonify({
                        "status": "success",
                        "api_keys": key_list
                    })
                    
            except Exception as e:
                self.logger.error(f"Get API keys error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/gateway/keys', methods=['POST'])
        @self.require_auth
        def create_api_key():
            """Create a new API key."""
            try:
                user_id = g.current_user_id
                data = request.get_json()
                
                # Generate API key
                api_key = f"odk_{uuid.uuid4().hex}"
                key_hash = hashlib.sha256(api_key.encode()).hexdigest()
                key_prefix = api_key[:12]
                
                expires_at = None
                if data.get('expires_in_days'):
                    expires_at = datetime.utcnow() + timedelta(days=data['expires_in_days'])
                
                with self.SessionLocal() as db:
                    key_record = APIKey(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        key_hash=key_hash,
                        key_prefix=key_prefix,
                        name=data.get('name'),
                        description=data.get('description', ''),
                        permissions=data.get('permissions', []),
                        rate_limit_per_minute=data.get('rate_limit_per_minute', 60),
                        rate_limit_per_hour=data.get('rate_limit_per_hour', 1000),
                        rate_limit_per_day=data.get('rate_limit_per_day', 10000),
                        expires_at=expires_at
                    )
                    
                    db.add(key_record)
                    db.commit()
                    
                    return jsonify({
                        "status": "success",
                        "api_key": api_key,  # Only returned once
                        "key_id": key_record.id,
                        "key_prefix": key_prefix
                    })
                    
            except Exception as e:
                self.logger.error(f"Create API key error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/gateway/keys/<key_id>', methods=['DELETE'])
        @self.require_auth
        def revoke_api_key(key_id):
            """Revoke an API key."""
            try:
                user_id = g.current_user_id
                
                with self.SessionLocal() as db:
                    key = db.query(APIKey).filter(
                        APIKey.id == key_id,
                        APIKey.user_id == user_id
                    ).first()
                    
                    if not key:
                        return jsonify({
                            "status": "error",
                            "message": "API key not found"
                        }), 404
                    
                    key.status = APIKeyStatus.REVOKED.value
                    db.commit()
                    
                    return jsonify({
                        "status": "success",
                        "message": "API key revoked successfully"
                    })
                    
            except Exception as e:
                self.logger.error(f"Revoke API key error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        # Webhook Management
        @self.app.route('/api/gateway/webhooks', methods=['GET'])
        @self.require_auth
        def get_webhooks():
            """Get user's webhooks."""
            try:
                user_id = g.current_user_id
                
                with self.SessionLocal() as db:
                    webhooks = db.query(Webhook).filter(
                        Webhook.user_id == user_id
                    ).all()
                    
                    webhook_list = []
                    for webhook in webhooks:
                        webhook_list.append({
                            "id": webhook.id,
                            "name": webhook.name,
                            "url": webhook.url,
                            "events": webhook.events,
                            "filters": webhook.filters,
                            "status": webhook.status,
                            "statistics": {
                                "total_deliveries": webhook.total_deliveries,
                                "successful_deliveries": webhook.successful_deliveries,
                                "failed_deliveries": webhook.failed_deliveries,
                                "success_rate": (webhook.successful_deliveries / webhook.total_deliveries * 100) if webhook.total_deliveries > 0 else 0
                            },
                            "last_delivery_at": webhook.last_delivery_at.isoformat() if webhook.last_delivery_at else None,
                            "created_at": webhook.created_at.isoformat()
                        })
                    
                    return jsonify({
                        "status": "success",
                        "webhooks": webhook_list
                    })
                    
            except Exception as e:
                self.logger.error(f"Get webhooks error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/gateway/webhooks', methods=['POST'])
        @self.require_auth
        def create_webhook():
            """Create a new webhook."""
            try:
                user_id = g.current_user_id
                data = request.get_json()
                
                # Generate webhook secret
                webhook_secret = f"whsec_{uuid.uuid4().hex}"
                
                with self.SessionLocal() as db:
                    webhook = Webhook(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        name=data.get('name'),
                        url=data.get('url'),
                        secret=webhook_secret,
                        events=data.get('events', []),
                        filters=data.get('filters', {}),
                        retry_count=data.get('retry_count', 3),
                        timeout_seconds=data.get('timeout_seconds', 30)
                    )
                    
                    db.add(webhook)
                    db.commit()
                    
                    return jsonify({
                        "status": "success",
                        "webhook_id": webhook.id,
                        "secret": webhook_secret
                    })
                    
            except Exception as e:
                self.logger.error(f"Create webhook error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/gateway/webhooks/<webhook_id>/test', methods=['POST'])
        @self.require_auth
        def test_webhook(webhook_id):
            """Test a webhook delivery."""
            try:
                user_id = g.current_user_id
                
                with self.SessionLocal() as db:
                    webhook = db.query(Webhook).filter(
                        Webhook.id == webhook_id,
                        Webhook.user_id == user_id
                    ).first()
                    
                    if not webhook:
                        return jsonify({
                            "status": "error",
                            "message": "Webhook not found"
                        }), 404
                    
                    # Send test payload
                    test_payload = {
                        "event": "webhook.test",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "message": "This is a test webhook delivery"
                        }
                    }
                    
                    success = self.deliver_webhook(webhook, "webhook.test", test_payload)
                    
                    return jsonify({
                        "status": "success" if success else "error",
                        "message": "Test webhook delivered successfully" if success else "Test webhook delivery failed"
                    })
                    
            except Exception as e:
                self.logger.error(f"Test webhook error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        # Integration Management
        @self.app.route('/api/gateway/integrations', methods=['GET'])
        @self.require_auth
        def get_integrations():
            """Get user's integrations."""
            try:
                user_id = g.current_user_id
                
                with self.SessionLocal() as db:
                    integrations = db.query(Integration).filter(
                        Integration.user_id == user_id
                    ).all()
                    
                    integration_list = []
                    for integration in integrations:
                        integration_list.append({
                            "id": integration.id,
                            "name": integration.name,
                            "integration_type": integration.integration_type,
                            "provider": integration.provider,
                            "is_active": integration.is_active,
                            "auto_sync": integration.auto_sync,
                            "sync_frequency_minutes": integration.sync_frequency_minutes,
                            "statistics": {
                                "total_syncs": integration.total_syncs,
                                "successful_syncs": integration.successful_syncs,
                                "failed_syncs": integration.failed_syncs,
                                "success_rate": (integration.successful_syncs / integration.total_syncs * 100) if integration.total_syncs > 0 else 0
                            },
                            "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
                            "created_at": integration.created_at.isoformat()
                        })
                    
                    return jsonify({
                        "status": "success",
                        "integrations": integration_list
                    })
                    
            except Exception as e:
                self.logger.error(f"Get integrations error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        # API Proxy Routes
        @self.app.route('/api/v1/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
        @self.require_api_key
        @self.limiter.limit("100 per minute")
        def api_proxy(endpoint):
            """Proxy API requests to appropriate services."""
            try:
                # Route to appropriate service based on endpoint
                if endpoint.startswith('forms'):
                    return self.proxy_to_service('form_management', endpoint)
                elif endpoint.startswith('submissions'):
                    return self.proxy_to_service('data_collection', endpoint)
                elif endpoint.startswith('analytics') or endpoint.startswith('data'):
                    return self.proxy_to_service('data_aggregation', endpoint)
                elif endpoint.startswith('dashboard') or endpoint.startswith('visualization'):
                    return self.proxy_to_service('dashboard', endpoint)
                elif endpoint.startswith('auth'):
                    return self.proxy_to_service('security', endpoint)
                elif endpoint.startswith('subscription'):
                    return self.proxy_to_service('subscription', endpoint)
                else:
                    return jsonify({
                        "status": "error",
                        "message": f"Unknown endpoint: {endpoint}"
                    }), 404
                    
            except Exception as e:
                self.logger.error(f"API proxy error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": "Internal server error"
                }), 500
    
    def _setup_error_handlers(self):
        """Setup error handlers for the API Gateway."""
        
        @self.app.errorhandler(TooManyRequests)
        def handle_rate_limit(e):
            return jsonify({
                "status": "error",
                "message": "Rate limit exceeded",
                "retry_after": e.retry_after
            }), 429
        
        @self.app.errorhandler(Unauthorized)
        def handle_unauthorized(e):
            return jsonify({
                "status": "error",
                "message": "Authentication required"
            }), 401
        
        @self.app.errorhandler(Forbidden)
        def handle_forbidden(e):
            return jsonify({
                "status": "error",
                "message": "Access forbidden"
            }), 403
        
        @self.app.errorhandler(404)
        def handle_not_found(e):
            return jsonify({
                "status": "error",
                "message": "Endpoint not found"
            }), 404
        
        @self.app.errorhandler(500)
        def handle_internal_error(e):
            return jsonify({
                "status": "error",
                "message": "Internal server error"
            }), 500
    
    def require_auth(self, f):
        """Decorator to require authentication."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for session token or JWT
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({
                    "status": "error",
                    "message": "Authentication required"
                }), 401
            
            token = auth_header.split(' ')[1]
            
            # Validate token (this would integrate with your auth system)
            user_id = self.validate_auth_token(token)
            if not user_id:
                return jsonify({
                    "status": "error",
                    "message": "Invalid authentication token"
                }), 401
            
            g.current_user_id = user_id
            return f(*args, **kwargs)
        
        return decorated_function
    
    def require_api_key(self, f):
        """Decorator to require API key authentication."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                return jsonify({
                    "status": "error",
                    "message": "API key required"
                }), 401
            
            # Validate API key
            key_info = self.validate_api_key(api_key)
            if not key_info:
                return jsonify({
                    "status": "error",
                    "message": "Invalid API key"
                }), 401
            
            # Check rate limits
            if not self.check_rate_limits(key_info):
                return jsonify({
                    "status": "error",
                    "message": "Rate limit exceeded for API key"
                }), 429
            
            g.current_api_key = key_info
            g.current_user_id = key_info['user_id']
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def validate_auth_token(self, token: str) -> Optional[str]:
        """Validate authentication token and return user ID."""
        # This would integrate with your authentication system
        # For now, return a placeholder
        return "user_123"
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return key information."""
        try:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            with self.SessionLocal() as db:
                key = db.query(APIKey).filter(
                    APIKey.key_hash == key_hash,
                    APIKey.status == APIKeyStatus.ACTIVE.value
                ).first()
                
                if not key:
                    return None
                
                # Check expiry
                if key.expires_at and key.expires_at < datetime.utcnow():
                    key.status = APIKeyStatus.EXPIRED.value
                    db.commit()
                    return None
                
                # Update usage
                key.total_requests += 1
                key.last_used_at = datetime.utcnow()
                db.commit()
                
                return {
                    "id": key.id,
                    "user_id": key.user_id,
                    "permissions": key.permissions,
                    "rate_limits": {
                        "per_minute": key.rate_limit_per_minute,
                        "per_hour": key.rate_limit_per_hour,
                        "per_day": key.rate_limit_per_day
                    }
                }
                
        except Exception as e:
            self.logger.error(f"API key validation error: {str(e)}")
            return None
    
    def check_rate_limits(self, key_info: Dict[str, Any]) -> bool:
        """Check if API key is within rate limits."""
        if not self.redis_client:
            return True  # No rate limiting without Redis
        
        key_id = key_info['id']
        limits = key_info['rate_limits']
        
        # Check minute limit
        minute_key = f"rate_limit:minute:{key_id}"
        minute_count = self.redis_client.get(minute_key)
        if minute_count and int(minute_count) >= limits['per_minute']:
            return False
        
        # Check hour limit
        hour_key = f"rate_limit:hour:{key_id}"
        hour_count = self.redis_client.get(hour_key)
        if hour_count and int(hour_count) >= limits['per_hour']:
            return False
        
        # Check day limit
        day_key = f"rate_limit:day:{key_id}"
        day_count = self.redis_client.get(day_key)
        if day_count and int(day_count) >= limits['per_day']:
            return False
        
        # Increment counters
        pipe = self.redis_client.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)
        pipe.incr(day_key)
        pipe.expire(day_key, 86400)
        pipe.execute()
        
        return True
    
    def proxy_to_service(self, service: str, endpoint: str) -> Response:
        """Proxy request to appropriate microservice."""
        # Service URL mapping
        service_urls = {
            'form_management': 'http://localhost:5000',
            'data_collection': 'http://localhost:5001',
            'data_aggregation': 'http://localhost:5002',
            'dashboard': 'http://localhost:5003',
            'security': 'http://localhost:5004',
            'subscription': 'http://localhost:5005'
        }
        
        base_url = service_urls.get(service)
        if not base_url:
            return jsonify({
                "status": "error",
                "message": f"Service not available: {service}"
            }), 503
        
        # Forward request
        url = f"{base_url}/api/{endpoint}"
        
        try:
            response = requests.request(
                method=request.method,
                url=url,
                headers={k: v for k, v in request.headers if k.lower() != 'host'},
                data=request.get_data(),
                params=request.args,
                timeout=30
            )
            
            # Log API usage for analytics
            self.log_api_usage(endpoint, response.status_code)
            
            return Response(
                response.content,
                status=response.status_code,
                headers=dict(response.headers)
            )
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Service proxy error: {str(e)}")
            return jsonify({
                "status": "error",
                "message": "Service unavailable"
            }), 503
    
    def deliver_webhook(self, webhook: Webhook, event_type: str, payload: Dict[str, Any]) -> bool:
        """Deliver webhook payload to endpoint."""
        try:
            # Create delivery record
            delivery_id = str(uuid.uuid4())
            
            # Prepare payload
            webhook_payload = {
                "id": delivery_id,
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": payload
            }
            
            # Create signature
            signature = self.create_webhook_signature(webhook.secret, json.dumps(webhook_payload))
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-ODK-Signature': signature,
                'X-ODK-Event': event_type,
                'X-ODK-Delivery': delivery_id,
                'User-Agent': 'ODK-MCP-Webhook/1.0'
            }
            
            start_time = time.time()
            
            # Send webhook
            response = requests.post(
                webhook.url,
                json=webhook_payload,
                headers=headers,
                timeout=webhook.timeout_seconds
            )
            
            delivery_duration = int((time.time() - start_time) * 1000)
            success = 200 <= response.status_code < 300
            
            # Record delivery
            with self.SessionLocal() as db:
                delivery = WebhookDelivery(
                    id=delivery_id,
                    webhook_id=webhook.id,
                    event_type=event_type,
                    payload=webhook_payload,
                    request_headers=headers,
                    request_body=json.dumps(webhook_payload),
                    response_status=response.status_code,
                    response_headers=dict(response.headers),
                    response_body=response.text[:1000],  # Limit response body size
                    delivery_duration_ms=delivery_duration,
                    success=success,
                    delivered_at=datetime.utcnow()
                )
                
                db.add(delivery)
                
                # Update webhook statistics
                webhook.total_deliveries += 1
                webhook.last_delivery_at = datetime.utcnow()
                
                if success:
                    webhook.successful_deliveries += 1
                    webhook.last_success_at = datetime.utcnow()
                else:
                    webhook.failed_deliveries += 1
                    webhook.last_failure_at = datetime.utcnow()
                    delivery.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                
                db.commit()
            
            return success
            
        except Exception as e:
            self.logger.error(f"Webhook delivery error: {str(e)}")
            
            # Record failed delivery
            with self.SessionLocal() as db:
                delivery = WebhookDelivery(
                    id=delivery_id,
                    webhook_id=webhook.id,
                    event_type=event_type,
                    payload=payload,
                    success=False,
                    error_message=str(e),
                    created_at=datetime.utcnow()
                )
                
                db.add(delivery)
                
                webhook.total_deliveries += 1
                webhook.failed_deliveries += 1
                webhook.last_delivery_at = datetime.utcnow()
                webhook.last_failure_at = datetime.utcnow()
                
                db.commit()
            
            return False
    
    def create_webhook_signature(self, secret: str, payload: str) -> str:
        """Create webhook signature for verification."""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def trigger_webhooks(self, event_type: str, data: Dict[str, Any], user_id: str = None):
        """Trigger webhooks for a specific event."""
        try:
            with self.SessionLocal() as db:
                query = db.query(Webhook).filter(
                    Webhook.status == WebhookStatus.ACTIVE.value
                )
                
                if user_id:
                    query = query.filter(Webhook.user_id == user_id)
                
                webhooks = query.all()
                
                for webhook in webhooks:
                    # Check if webhook is subscribed to this event
                    if event_type in webhook.events or '*' in webhook.events:
                        # Apply filters if any
                        if self.webhook_matches_filters(data, webhook.filters):
                            # Add to delivery queue
                            self.webhook_queue.append({
                                'webhook': webhook,
                                'event_type': event_type,
                                'data': data
                            })
                
        except Exception as e:
            self.logger.error(f"Webhook trigger error: {str(e)}")
    
    def webhook_matches_filters(self, data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if webhook data matches filters."""
        if not filters:
            return True
        
        for key, expected_value in filters.items():
            if key not in data or data[key] != expected_value:
                return False
        
        return True
    
    def log_api_usage(self, endpoint: str, status_code: int):
        """Log API usage for analytics."""
        # This would integrate with your analytics system
        pass
    
    def run(self, host='0.0.0.0', port=5006, debug=False):
        """Run the API Gateway application."""
        self.app.run(host=host, port=port, debug=debug)


# Create a global instance
api_gateway = APIGateway()

