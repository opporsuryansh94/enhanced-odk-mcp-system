"""
Security and Governance Configuration for ODK MCP System.
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
KEYS_DIR = os.path.join(BASE_DIR, "keys")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Ensure directories exist
os.makedirs(KEYS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Authentication configuration
AUTHENTICATION = {
    # JWT settings
    "jwt_secret_key": os.environ.get("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production"),
    "jwt_algorithm": "HS256",
    "jwt_expiration_hours": 24,
    "jwt_refresh_expiration_days": 30,
    
    # Session settings
    "session_timeout_minutes": 60,
    "max_concurrent_sessions": 5,
    "session_encryption_key": os.environ.get("SESSION_ENCRYPTION_KEY", "your-session-encryption-key"),
    
    # Password policy
    "password_min_length": 8,
    "password_require_uppercase": True,
    "password_require_lowercase": True,
    "password_require_numbers": True,
    "password_require_special_chars": True,
    "password_history_count": 5,
    "password_expiry_days": 90,
    
    # Account lockout
    "max_login_attempts": 5,
    "lockout_duration_minutes": 30,
    "lockout_escalation_enabled": True,
    
    # Two-factor authentication
    "2fa_enabled": True,
    "2fa_issuer": "ODK MCP System",
    "2fa_backup_codes_count": 10,
    "2fa_grace_period_days": 7,
}

# Encryption configuration
ENCRYPTION = {
    # Field-level encryption
    "field_encryption_enabled": True,
    "encryption_algorithm": "AES-256-GCM",
    "encryption_key": os.environ.get("FIELD_ENCRYPTION_KEY", "your-field-encryption-key-32-chars"),
    "key_rotation_enabled": True,
    "key_rotation_interval_days": 90,
    
    # Database encryption
    "database_encryption_enabled": True,
    "database_encryption_key": os.environ.get("DATABASE_ENCRYPTION_KEY", "your-database-encryption-key"),
    
    # File encryption
    "file_encryption_enabled": True,
    "file_encryption_algorithm": "AES-256-CBC",
    
    # Encryption at rest
    "encrypt_sensitive_fields": [
        "email",
        "phone",
        "personal_data",
        "financial_data",
        "health_data",
        "location_data"
    ]
}

# Audit and logging configuration
AUDIT = {
    # Audit logging
    "audit_enabled": True,
    "audit_log_file": os.path.join(LOGS_DIR, "audit.log"),
    "audit_log_level": "INFO",
    "audit_log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "audit_log_rotation": True,
    "audit_log_max_size_mb": 100,
    "audit_log_backup_count": 10,
    
    # Events to audit
    "audit_events": [
        "user_login",
        "user_logout",
        "user_registration",
        "password_change",
        "2fa_setup",
        "2fa_disable",
        "form_create",
        "form_update",
        "form_delete",
        "form_publish",
        "data_export",
        "data_import",
        "user_role_change",
        "permission_change",
        "system_config_change",
        "api_key_create",
        "api_key_revoke",
        "subscription_change",
        "payment_processed"
    ],
    
    # Data retention
    "audit_retention_days": 2555,  # 7 years for compliance
    "log_retention_days": 365,
    "backup_retention_days": 2555,
    
    # Real-time monitoring
    "real_time_alerts_enabled": True,
    "suspicious_activity_threshold": 10,
    "failed_login_alert_threshold": 5,
}

# GDPR and privacy configuration
GDPR = {
    # Data protection
    "gdpr_compliance_enabled": True,
    "data_retention_policy_enabled": True,
    "right_to_be_forgotten_enabled": True,
    "data_portability_enabled": True,
    "consent_management_enabled": True,
    
    # Data retention periods (in days)
    "user_data_retention_days": 2555,  # 7 years
    "form_data_retention_days": 1825,  # 5 years
    "audit_data_retention_days": 2555,  # 7 years
    "session_data_retention_days": 30,
    "temporary_data_retention_days": 7,
    
    # Data processing lawful bases
    "lawful_bases": [
        "consent",
        "contract",
        "legal_obligation",
        "vital_interests",
        "public_task",
        "legitimate_interests"
    ],
    
    # Data categories
    "data_categories": [
        "personal_identifiers",
        "contact_information",
        "demographic_data",
        "location_data",
        "behavioral_data",
        "technical_data",
        "usage_data",
        "communication_data"
    ],
    
    # Privacy settings
    "anonymization_enabled": True,
    "pseudonymization_enabled": True,
    "data_minimization_enabled": True,
    "purpose_limitation_enabled": True,
}

# Access control configuration
ACCESS_CONTROL = {
    # Role-based access control (RBAC)
    "rbac_enabled": True,
    "default_role": "user",
    "role_hierarchy": {
        "super_admin": 100,
        "admin": 80,
        "manager": 60,
        "analyst": 40,
        "user": 20,
        "viewer": 10
    },
    
    # Permissions
    "permissions": {
        # User management
        "user.create": ["super_admin", "admin"],
        "user.read": ["super_admin", "admin", "manager"],
        "user.update": ["super_admin", "admin"],
        "user.delete": ["super_admin"],
        
        # Form management
        "form.create": ["super_admin", "admin", "manager", "analyst", "user"],
        "form.read": ["super_admin", "admin", "manager", "analyst", "user", "viewer"],
        "form.update": ["super_admin", "admin", "manager", "analyst", "user"],
        "form.delete": ["super_admin", "admin", "manager", "user"],
        "form.publish": ["super_admin", "admin", "manager", "user"],
        
        # Data management
        "data.create": ["super_admin", "admin", "manager", "analyst", "user"],
        "data.read": ["super_admin", "admin", "manager", "analyst", "user", "viewer"],
        "data.update": ["super_admin", "admin", "manager", "analyst", "user"],
        "data.delete": ["super_admin", "admin", "manager"],
        "data.export": ["super_admin", "admin", "manager", "analyst"],
        
        # System administration
        "system.config": ["super_admin"],
        "system.logs": ["super_admin", "admin"],
        "system.backup": ["super_admin", "admin"],
        "system.restore": ["super_admin"],
        
        # Analytics and reporting
        "analytics.view": ["super_admin", "admin", "manager", "analyst"],
        "analytics.export": ["super_admin", "admin", "manager", "analyst"],
        "reports.create": ["super_admin", "admin", "manager", "analyst"],
        "reports.share": ["super_admin", "admin", "manager"],
        
        # API access
        "api.read": ["super_admin", "admin", "manager", "analyst", "user"],
        "api.write": ["super_admin", "admin", "manager", "user"],
        "api.admin": ["super_admin", "admin"],
    },
    
    # Organization-level access
    "organization_isolation_enabled": True,
    "cross_organization_access_enabled": False,
    "organization_admin_role": "admin",
    
    # IP restrictions
    "ip_whitelist_enabled": False,
    "ip_whitelist": [],
    "ip_blacklist_enabled": True,
    "ip_blacklist": [],
    
    # Time-based access
    "time_based_access_enabled": False,
    "allowed_hours": {
        "start": "09:00",
        "end": "18:00"
    },
    "allowed_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
}

# Security headers and policies
SECURITY_HEADERS = {
    # Content Security Policy
    "csp_enabled": True,
    "csp_policy": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "https:"],
        "connect-src": ["'self'"],
        "frame-ancestors": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"]
    },
    
    # Other security headers
    "hsts_enabled": True,
    "hsts_max_age": 31536000,  # 1 year
    "hsts_include_subdomains": True,
    "hsts_preload": True,
    
    "x_frame_options": "DENY",
    "x_content_type_options": "nosniff",
    "x_xss_protection": "1; mode=block",
    "referrer_policy": "strict-origin-when-cross-origin",
    "permissions_policy": "geolocation=(), microphone=(), camera=()",
}

# API security configuration
API_SECURITY = {
    # Rate limiting
    "rate_limiting_enabled": True,
    "rate_limit_per_minute": 60,
    "rate_limit_per_hour": 1000,
    "rate_limit_per_day": 10000,
    "rate_limit_burst": 10,
    
    # API authentication
    "api_key_required": True,
    "api_key_header": "X-API-Key",
    "api_key_expiry_days": 365,
    "api_key_rotation_enabled": True,
    
    # Request validation
    "request_size_limit_mb": 10,
    "request_timeout_seconds": 30,
    "input_validation_enabled": True,
    "output_sanitization_enabled": True,
    
    # CORS settings
    "cors_enabled": True,
    "cors_origins": ["*"],  # Configure for production
    "cors_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "cors_headers": ["Content-Type", "Authorization", "X-API-Key"],
    "cors_credentials": True,
}

# Backup and disaster recovery
BACKUP = {
    # Backup configuration
    "backup_enabled": True,
    "backup_schedule": "0 2 * * *",  # Daily at 2 AM
    "backup_retention_days": 30,
    "backup_encryption_enabled": True,
    "backup_compression_enabled": True,
    
    # Backup types
    "database_backup_enabled": True,
    "file_backup_enabled": True,
    "config_backup_enabled": True,
    "logs_backup_enabled": True,
    
    # Storage locations
    "backup_local_path": os.path.join(BASE_DIR, "backups"),
    "backup_remote_enabled": False,
    "backup_remote_provider": "s3",  # s3, azure, gcp
    "backup_remote_config": {},
    
    # Disaster recovery
    "disaster_recovery_enabled": True,
    "recovery_point_objective_hours": 24,
    "recovery_time_objective_hours": 4,
    "automated_failover_enabled": False,
}

# Compliance frameworks
COMPLIANCE = {
    # Supported frameworks
    "frameworks": ["GDPR", "HIPAA", "SOC2", "ISO27001"],
    
    # GDPR specific
    "gdpr_dpo_contact": "dpo@odkmcp.com",
    "gdpr_privacy_policy_url": "https://odkmcp.com/privacy",
    "gdpr_cookie_policy_url": "https://odkmcp.com/cookies",
    
    # HIPAA specific (if handling health data)
    "hipaa_enabled": False,
    "hipaa_business_associate_agreement": False,
    "hipaa_minimum_necessary_standard": True,
    
    # SOC2 specific
    "soc2_enabled": True,
    "soc2_trust_principles": ["security", "availability", "processing_integrity", "confidentiality", "privacy"],
    
    # ISO27001 specific
    "iso27001_enabled": True,
    "iso27001_risk_assessment_enabled": True,
    "iso27001_incident_management_enabled": True,
}

# Monitoring and alerting
MONITORING = {
    # Security monitoring
    "security_monitoring_enabled": True,
    "intrusion_detection_enabled": True,
    "anomaly_detection_enabled": True,
    "threat_intelligence_enabled": True,
    
    # Alert thresholds
    "failed_login_threshold": 5,
    "suspicious_activity_threshold": 10,
    "data_breach_detection_enabled": True,
    "unusual_access_pattern_detection": True,
    
    # Notification channels
    "email_alerts_enabled": True,
    "sms_alerts_enabled": False,
    "webhook_alerts_enabled": True,
    "slack_alerts_enabled": False,
    
    # Alert recipients
    "security_team_email": "security@odkmcp.com",
    "admin_email": "admin@odkmcp.com",
    "emergency_contact": "+91 98765 43210",
}

# Vulnerability management
VULNERABILITY_MANAGEMENT = {
    # Scanning
    "vulnerability_scanning_enabled": True,
    "dependency_scanning_enabled": True,
    "code_scanning_enabled": True,
    "infrastructure_scanning_enabled": True,
    
    # Patch management
    "automated_patching_enabled": False,
    "patch_testing_required": True,
    "critical_patch_window_hours": 24,
    "regular_patch_window_days": 30,
    
    # Penetration testing
    "penetration_testing_enabled": True,
    "penetration_testing_frequency_months": 6,
    "bug_bounty_program_enabled": False,
}

# Incident response
INCIDENT_RESPONSE = {
    # Incident management
    "incident_response_enabled": True,
    "incident_classification_enabled": True,
    "automated_incident_detection": True,
    "incident_escalation_enabled": True,
    
    # Response team
    "incident_response_team": [
        "security@odkmcp.com",
        "admin@odkmcp.com",
        "legal@odkmcp.com"
    ],
    
    # Response procedures
    "incident_response_plan_url": "https://odkmcp.com/incident-response",
    "data_breach_notification_enabled": True,
    "regulatory_notification_enabled": True,
    "customer_notification_enabled": True,
    
    # Recovery procedures
    "automated_recovery_enabled": False,
    "backup_restoration_enabled": True,
    "forensic_analysis_enabled": True,
}


