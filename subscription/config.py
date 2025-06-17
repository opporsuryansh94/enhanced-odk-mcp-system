"""
Configuration for the subscription-based access control system.
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)

# Payment gateway configuration
PAYMENT_GATEWAYS = {
    # Razorpay configuration (primary for India)
    "razorpay": {
        "enabled": True,
        "key_id": os.environ.get("RAZORPAY_KEY_ID", ""),
        "key_secret": os.environ.get("RAZORPAY_KEY_SECRET", ""),
        "webhook_secret": os.environ.get("RAZORPAY_WEBHOOK_SECRET", ""),
        "test_mode": True,  # Set to False in production
    },
    
    # Stripe configuration (alternative)
    "stripe": {
        "enabled": False,  # Set to True to enable Stripe
        "publishable_key": os.environ.get("STRIPE_PUBLISHABLE_KEY", ""),
        "secret_key": os.environ.get("STRIPE_SECRET_KEY", ""),
        "webhook_secret": os.environ.get("STRIPE_WEBHOOK_SECRET", ""),
        "test_mode": True,  # Set to False in production
    }
}

# Subscription plans configuration
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free",
        "description": "Basic access for individuals and small projects",
        "price_monthly": 0,
        "price_yearly": 0,
        "currency": "INR",
        "features": [
            "5 forms",
            "100 submissions per month",
            "Basic analytics",
            "No API access",
            "Community support"
        ],
        "limits": {
            "forms": 5,
            "submissions_per_month": 100,
            "api_calls_per_day": 0,
            "storage_mb": 100,
            "users": 1
        }
    },
    "starter": {
        "name": "Starter",
        "description": "For small teams and organizations",
        "price_monthly": 999,
        "price_yearly": 9990,  # 10 months for yearly subscription
        "currency": "INR",
        "features": [
            "20 forms",
            "1,000 submissions per month",
            "Basic analytics",
            "Limited API access",
            "Email support"
        ],
        "limits": {
            "forms": 20,
            "submissions_per_month": 1000,
            "api_calls_per_day": 100,
            "storage_mb": 500,
            "users": 5
        }
    },
    "pro": {
        "name": "Pro",
        "description": "For growing organizations with advanced needs",
        "price_monthly": 2999,
        "price_yearly": 29990,  # 10 months for yearly subscription
        "currency": "INR",
        "features": [
            "100 forms",
            "10,000 submissions per month",
            "Advanced analytics",
            "Full API access",
            "Priority support",
            "AI-powered insights"
        ],
        "limits": {
            "forms": 100,
            "submissions_per_month": 10000,
            "api_calls_per_day": 1000,
            "storage_mb": 2048,
            "users": 20
        }
    },
    "enterprise": {
        "name": "Enterprise",
        "description": "For large organizations with custom requirements",
        "price_monthly": 9999,
        "price_yearly": 99990,  # 10 months for yearly subscription
        "currency": "INR",
        "features": [
            "Unlimited forms",
            "Unlimited submissions",
            "Advanced analytics with custom reports",
            "Full API access with higher rate limits",
            "Dedicated support",
            "Custom branding options",
            "All AI features"
        ],
        "limits": {
            "forms": -1,  # Unlimited
            "submissions_per_month": -1,  # Unlimited
            "api_calls_per_day": 10000,
            "storage_mb": 10240,
            "users": 100
        }
    }
}

# Billing configuration
BILLING = {
    "invoice_prefix": "ODK-INV-",
    "default_currency": "INR",
    "tax_rate": 18.0,  # GST in India
    "grace_period_days": 7,
    "retry_attempts": 3,
    "retry_interval_days": 3,
    "invoice_due_days": 15,
    "invoice_template_path": os.path.join(BASE_DIR, "templates", "invoice_template.html"),
}

# Usage tracking configuration
USAGE_TRACKING = {
    "track_form_count": True,
    "track_submission_count": True,
    "track_api_calls": True,
    "track_storage": True,
    "track_user_count": True,
    "reset_counters_on_billing_date": True,
    "usage_alert_threshold": 0.8,  # Send alert when 80% of limit is reached
}

# Feature access configuration
FEATURE_ACCESS = {
    "free": {
        "advanced_analytics": False,
        "api_access": False,
        "custom_branding": False,
        "data_export": True,
        "form_templates": False,
        "multilingual_support": True,
        "offline_collection": True,
        "priority_support": False,
        "smart_form_builder": False,
        "virtual_assistant": False,
    },
    "starter": {
        "advanced_analytics": False,
        "api_access": True,
        "custom_branding": False,
        "data_export": True,
        "form_templates": True,
        "multilingual_support": True,
        "offline_collection": True,
        "priority_support": False,
        "smart_form_builder": True,
        "virtual_assistant": False,
    },
    "pro": {
        "advanced_analytics": True,
        "api_access": True,
        "custom_branding": False,
        "data_export": True,
        "form_templates": True,
        "multilingual_support": True,
        "offline_collection": True,
        "priority_support": True,
        "smart_form_builder": True,
        "virtual_assistant": True,
    },
    "enterprise": {
        "advanced_analytics": True,
        "api_access": True,
        "custom_branding": True,
        "data_export": True,
        "form_templates": True,
        "multilingual_support": True,
        "offline_collection": True,
        "priority_support": True,
        "smart_form_builder": True,
        "virtual_assistant": True,
    }
}

# Logging configuration
LOGGING = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": os.path.join(BASE_DIR, "subscription.log"),
}

