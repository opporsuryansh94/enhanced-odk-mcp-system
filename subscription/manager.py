"""
Enhanced Subscription Management System for ODK MCP System.
Provides comprehensive SaaS monetization with payment processing, billing, and usage tracking.
"""

import os
import json
import uuid
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import logging
from dataclasses import dataclass, asdict
from enum import Enum

import razorpay
import stripe
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from .config import SUBSCRIPTION_PLANS, PAYMENT_GATEWAYS, BILLING, USAGE_TRACKING, FEATURE_ACCESS


# Database Models
Base = declarative_base()


class SubscriptionStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class UsageMetrics:
    forms_count: int = 0
    submissions_count: int = 0
    api_calls_count: int = 0
    storage_mb: float = 0.0
    users_count: int = 0
    period_start: datetime = None
    period_end: datetime = None


class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    organization = Column(String)
    phone = Column(String)
    country = Column(String, default='IN')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)


class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    plan_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    cancelled_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Payment gateway specific IDs
    razorpay_subscription_id = Column(String)
    stripe_subscription_id = Column(String)
    
    # Billing details
    billing_cycle = Column(String, default='monthly')  # monthly, yearly
    next_billing_date = Column(DateTime)
    auto_renew = Column(Boolean, default=True)


class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    subscription_id = Column(String)
    amount = Column(Float, nullable=False)
    currency = Column(String, default='INR')
    status = Column(String, nullable=False)
    payment_method = Column(String)
    gateway = Column(String, nullable=False)  # razorpay, stripe
    gateway_payment_id = Column(String)
    gateway_order_id = Column(String)
    description = Column(Text)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Invoice details
    invoice_id = Column(String)
    invoice_url = Column(String)


class Usage(Base):
    __tablename__ = 'usage'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    subscription_id = Column(String)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Usage metrics
    forms_count = Column(Integer, default=0)
    submissions_count = Column(Integer, default=0)
    api_calls_count = Column(Integer, default=0)
    storage_mb = Column(Float, default=0.0)
    users_count = Column(Integer, default=1)
    
    # Metadata
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Invoice(Base):
    __tablename__ = 'invoices'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    subscription_id = Column(String)
    invoice_number = Column(String, unique=True, nullable=False)
    amount_subtotal = Column(Float, nullable=False)
    amount_tax = Column(Float, default=0.0)
    amount_total = Column(Float, nullable=False)
    currency = Column(String, default='INR')
    status = Column(String, default='draft')  # draft, sent, paid, overdue, cancelled
    due_date = Column(DateTime)
    paid_at = Column(DateTime)
    
    # Line items (JSON)
    line_items = Column(JSON)
    
    # PDF and URLs
    pdf_url = Column(String)
    hosted_url = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SubscriptionManager:
    """
    Comprehensive subscription management system with payment processing and usage tracking.
    """
    
    def __init__(self, database_url: str = "sqlite:///subscription.db"):
        """
        Initialize the subscription manager.
        
        Args:
            database_url: Database connection URL.
        """
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize payment gateways
        self.razorpay_client = None
        self.stripe_client = None
        
        if PAYMENT_GATEWAYS["razorpay"]["enabled"]:
            self.razorpay_client = razorpay.Client(
                auth=(
                    PAYMENT_GATEWAYS["razorpay"]["key_id"],
                    PAYMENT_GATEWAYS["razorpay"]["key_secret"]
                )
            )
        
        if PAYMENT_GATEWAYS["stripe"]["enabled"]:
            stripe.api_key = PAYMENT_GATEWAYS["stripe"]["secret_key"]
            self.stripe_client = stripe
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, BILLING["level"]),
            format=BILLING["format"],
            filename=BILLING["file"]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize Flask app
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes for subscription management."""
        
        @self.app.route('/api/subscription/plans')
        def get_plans():
            """Get available subscription plans."""
            return jsonify({
                "status": "success",
                "plans": SUBSCRIPTION_PLANS
            })
        
        @self.app.route('/api/subscription/user/<user_id>')
        def get_user_subscription(user_id):
            """Get user's current subscription."""
            try:
                with self.SessionLocal() as db:
                    subscription = self.get_active_subscription(db, user_id)
                    
                    if not subscription:
                        return jsonify({
                            "status": "success",
                            "subscription": None,
                            "plan": SUBSCRIPTION_PLANS["free"]
                        })
                    
                    plan = SUBSCRIPTION_PLANS.get(subscription.plan_id, SUBSCRIPTION_PLANS["free"])
                    usage = self.get_current_usage(db, user_id)
                    
                    return jsonify({
                        "status": "success",
                        "subscription": {
                            "id": subscription.id,
                            "plan_id": subscription.plan_id,
                            "status": subscription.status,
                            "current_period_start": subscription.current_period_start.isoformat(),
                            "current_period_end": subscription.current_period_end.isoformat(),
                            "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
                            "auto_renew": subscription.auto_renew
                        },
                        "plan": plan,
                        "usage": asdict(usage) if usage else None
                    })
                    
            except Exception as e:
                self.logger.error(f"Error getting user subscription: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/subscription/create', methods=['POST'])
        def create_subscription():
            """Create a new subscription."""
            try:
                data = request.get_json()
                user_id = data.get("user_id")
                plan_id = data.get("plan_id")
                billing_cycle = data.get("billing_cycle", "monthly")
                payment_method = data.get("payment_method", "razorpay")
                
                if not user_id or not plan_id:
                    return jsonify({
                        "status": "error",
                        "message": "user_id and plan_id are required"
                    }), 400
                
                if plan_id not in SUBSCRIPTION_PLANS:
                    return jsonify({
                        "status": "error",
                        "message": "Invalid plan_id"
                    }), 400
                
                with self.SessionLocal() as db:
                    result = self.create_subscription_with_payment(
                        db, user_id, plan_id, billing_cycle, payment_method
                    )
                    
                    return jsonify({
                        "status": "success",
                        "subscription": result["subscription"],
                        "payment_details": result["payment_details"]
                    })
                    
            except Exception as e:
                self.logger.error(f"Error creating subscription: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/subscription/cancel', methods=['POST'])
        def cancel_subscription():
            """Cancel a subscription."""
            try:
                data = request.get_json()
                user_id = data.get("user_id")
                immediate = data.get("immediate", False)
                
                if not user_id:
                    return jsonify({
                        "status": "error",
                        "message": "user_id is required"
                    }), 400
                
                with self.SessionLocal() as db:
                    result = self.cancel_user_subscription(db, user_id, immediate)
                    
                    return jsonify({
                        "status": "success",
                        "message": "Subscription cancelled successfully",
                        "subscription": result
                    })
                    
            except Exception as e:
                self.logger.error(f"Error cancelling subscription: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/subscription/usage/<user_id>')
        def get_usage(user_id):
            """Get user's current usage metrics."""
            try:
                with self.SessionLocal() as db:
                    usage = self.get_current_usage(db, user_id)
                    subscription = self.get_active_subscription(db, user_id)
                    
                    plan_id = subscription.plan_id if subscription else "free"
                    plan = SUBSCRIPTION_PLANS[plan_id]
                    
                    # Calculate usage percentages
                    usage_percentages = {}
                    if usage:
                        for metric, limit in plan["limits"].items():
                            if limit > 0:  # Skip unlimited (-1) limits
                                current_value = getattr(usage, metric, 0)
                                usage_percentages[metric] = (current_value / limit) * 100
                    
                    return jsonify({
                        "status": "success",
                        "usage": asdict(usage) if usage else None,
                        "limits": plan["limits"],
                        "usage_percentages": usage_percentages
                    })
                    
            except Exception as e:
                self.logger.error(f"Error getting usage: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/subscription/track-usage', methods=['POST'])
        def track_usage():
            """Track usage for a user."""
            try:
                data = request.get_json()
                user_id = data.get("user_id")
                metric = data.get("metric")
                value = data.get("value", 1)
                
                if not user_id or not metric:
                    return jsonify({
                        "status": "error",
                        "message": "user_id and metric are required"
                    }), 400
                
                with self.SessionLocal() as db:
                    self.track_usage_metric(db, user_id, metric, value)
                    
                    return jsonify({
                        "status": "success",
                        "message": "Usage tracked successfully"
                    })
                    
            except Exception as e:
                self.logger.error(f"Error tracking usage: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/subscription/check-access', methods=['POST'])
        def check_feature_access():
            """Check if user has access to a specific feature."""
            try:
                data = request.get_json()
                user_id = data.get("user_id")
                feature = data.get("feature")
                
                if not user_id or not feature:
                    return jsonify({
                        "status": "error",
                        "message": "user_id and feature are required"
                    }), 400
                
                with self.SessionLocal() as db:
                    has_access = self.check_feature_access(db, user_id, feature)
                    
                    return jsonify({
                        "status": "success",
                        "has_access": has_access
                    })
                    
            except Exception as e:
                self.logger.error(f"Error checking feature access: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/subscription/webhook/razorpay', methods=['POST'])
        def razorpay_webhook():
            """Handle Razorpay webhooks."""
            try:
                payload = request.get_data()
                signature = request.headers.get('X-Razorpay-Signature')
                
                # Verify webhook signature
                if not self.verify_razorpay_signature(payload, signature):
                    return jsonify({"status": "error", "message": "Invalid signature"}), 400
                
                event = request.get_json()
                self.handle_razorpay_webhook(event)
                
                return jsonify({"status": "success"})
                
            except Exception as e:
                self.logger.error(f"Error handling Razorpay webhook: {str(e)}")
                return jsonify({"status": "error", "message": str(e)}), 500
        
        @self.app.route('/api/subscription/webhook/stripe', methods=['POST'])
        def stripe_webhook():
            """Handle Stripe webhooks."""
            try:
                payload = request.get_data()
                signature = request.headers.get('Stripe-Signature')
                
                # Verify webhook signature
                event = stripe.Webhook.construct_event(
                    payload, signature, PAYMENT_GATEWAYS["stripe"]["webhook_secret"]
                )
                
                self.handle_stripe_webhook(event)
                
                return jsonify({"status": "success"})
                
            except Exception as e:
                self.logger.error(f"Error handling Stripe webhook: {str(e)}")
                return jsonify({"status": "error", "message": str(e)}), 500
        
        @self.app.route('/api/subscription/invoices/<user_id>')
        def get_user_invoices(user_id):
            """Get user's invoices."""
            try:
                with self.SessionLocal() as db:
                    invoices = db.query(Invoice).filter(
                        Invoice.user_id == user_id
                    ).order_by(Invoice.created_at.desc()).all()
                    
                    invoice_list = []
                    for invoice in invoices:
                        invoice_list.append({
                            "id": invoice.id,
                            "invoice_number": invoice.invoice_number,
                            "amount_total": invoice.amount_total,
                            "currency": invoice.currency,
                            "status": invoice.status,
                            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                            "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
                            "pdf_url": invoice.pdf_url,
                            "created_at": invoice.created_at.isoformat()
                        })
                    
                    return jsonify({
                        "status": "success",
                        "invoices": invoice_list
                    })
                    
            except Exception as e:
                self.logger.error(f"Error getting user invoices: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
    
    def create_subscription_with_payment(
        self, 
        db: Session, 
        user_id: str, 
        plan_id: str, 
        billing_cycle: str = "monthly",
        payment_method: str = "razorpay"
    ) -> Dict[str, Any]:
        """
        Create a new subscription with payment setup.
        
        Args:
            db: Database session.
            user_id: User ID.
            plan_id: Subscription plan ID.
            billing_cycle: Billing cycle (monthly/yearly).
            payment_method: Payment method (razorpay/stripe).
            
        Returns:
            Dictionary containing subscription and payment details.
        """
        plan = SUBSCRIPTION_PLANS[plan_id]
        
        # Calculate amount based on billing cycle
        if billing_cycle == "yearly":
            amount = plan["price_yearly"]
        else:
            amount = plan["price_monthly"]
        
        # Create subscription record
        subscription_id = str(uuid.uuid4())
        current_time = datetime.utcnow()
        
        if billing_cycle == "yearly":
            period_end = current_time + timedelta(days=365)
        else:
            period_end = current_time + timedelta(days=30)
        
        subscription = Subscription(
            id=subscription_id,
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.ACTIVE.value,
            current_period_start=current_time,
            current_period_end=period_end,
            billing_cycle=billing_cycle,
            next_billing_date=period_end,
            auto_renew=True
        )
        
        # Create payment order
        payment_details = None
        if amount > 0:  # Skip payment for free plan
            if payment_method == "razorpay" and self.razorpay_client:
                payment_details = self.create_razorpay_order(amount, plan["currency"], subscription_id)
            elif payment_method == "stripe" and self.stripe_client:
                payment_details = self.create_stripe_payment_intent(amount, plan["currency"], subscription_id)
        
        db.add(subscription)
        db.commit()
        
        # Initialize usage tracking
        self.initialize_usage_tracking(db, user_id, subscription_id)
        
        return {
            "subscription": {
                "id": subscription.id,
                "plan_id": subscription.plan_id,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start.isoformat(),
                "current_period_end": subscription.current_period_end.isoformat(),
                "billing_cycle": subscription.billing_cycle
            },
            "payment_details": payment_details
        }
    
    def create_razorpay_order(self, amount: float, currency: str, subscription_id: str) -> Dict[str, Any]:
        """Create Razorpay order for payment."""
        try:
            order_data = {
                "amount": int(amount * 100),  # Amount in paise
                "currency": currency,
                "receipt": f"sub_{subscription_id}",
                "notes": {
                    "subscription_id": subscription_id
                }
            }
            
            order = self.razorpay_client.order.create(data=order_data)
            
            return {
                "gateway": "razorpay",
                "order_id": order["id"],
                "amount": amount,
                "currency": currency,
                "key": PAYMENT_GATEWAYS["razorpay"]["key_id"]
            }
            
        except Exception as e:
            self.logger.error(f"Error creating Razorpay order: {str(e)}")
            raise
    
    def create_stripe_payment_intent(self, amount: float, currency: str, subscription_id: str) -> Dict[str, Any]:
        """Create Stripe payment intent for payment."""
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Amount in smallest currency unit
                currency=currency.lower(),
                metadata={
                    "subscription_id": subscription_id
                }
            )
            
            return {
                "gateway": "stripe",
                "client_secret": intent.client_secret,
                "amount": amount,
                "currency": currency,
                "publishable_key": PAYMENT_GATEWAYS["stripe"]["publishable_key"]
            }
            
        except Exception as e:
            self.logger.error(f"Error creating Stripe payment intent: {str(e)}")
            raise
    
    def get_active_subscription(self, db: Session, user_id: str) -> Optional[Subscription]:
        """Get user's active subscription."""
        return db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.ACTIVE.value
        ).first()
    
    def get_current_usage(self, db: Session, user_id: str) -> Optional[UsageMetrics]:
        """Get user's current usage metrics."""
        current_time = datetime.utcnow()
        
        # Get current billing period
        subscription = self.get_active_subscription(db, user_id)
        if subscription:
            period_start = subscription.current_period_start
            period_end = subscription.current_period_end
        else:
            # For free users, use monthly periods
            period_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        
        usage = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.period_start <= current_time,
            Usage.period_end > current_time
        ).first()
        
        if usage:
            return UsageMetrics(
                forms_count=usage.forms_count,
                submissions_count=usage.submissions_count,
                api_calls_count=usage.api_calls_count,
                storage_mb=usage.storage_mb,
                users_count=usage.users_count,
                period_start=usage.period_start,
                period_end=usage.period_end
            )
        
        return None
    
    def track_usage_metric(self, db: Session, user_id: str, metric: str, value: float = 1) -> None:
        """Track usage metric for a user."""
        current_time = datetime.utcnow()
        
        # Get or create current usage record
        subscription = self.get_active_subscription(db, user_id)
        if subscription:
            period_start = subscription.current_period_start
            period_end = subscription.current_period_end
        else:
            # For free users, use monthly periods
            period_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if period_start.month == 12:
                period_end = period_start.replace(year=period_start.year + 1, month=1)
            else:
                period_end = period_start.replace(month=period_start.month + 1)
        
        usage = db.query(Usage).filter(
            Usage.user_id == user_id,
            Usage.period_start <= current_time,
            Usage.period_end > current_time
        ).first()
        
        if not usage:
            usage = Usage(
                id=str(uuid.uuid4()),
                user_id=user_id,
                subscription_id=subscription.id if subscription else None,
                period_start=period_start,
                period_end=period_end
            )
            db.add(usage)
        
        # Update the specific metric
        if hasattr(usage, metric):
            current_value = getattr(usage, metric)
            setattr(usage, metric, current_value + value)
        
        db.commit()
        
        # Check for usage alerts
        self.check_usage_alerts(db, user_id, usage)
    
    def check_feature_access(self, db: Session, user_id: str, feature: str) -> bool:
        """Check if user has access to a specific feature."""
        subscription = self.get_active_subscription(db, user_id)
        
        if subscription:
            plan_id = subscription.plan_id
        else:
            plan_id = "free"
        
        feature_access = FEATURE_ACCESS.get(plan_id, FEATURE_ACCESS["free"])
        return feature_access.get(feature, False)
    
    def check_usage_limits(self, db: Session, user_id: str, metric: str) -> Tuple[bool, float]:
        """
        Check if user has exceeded usage limits.
        
        Returns:
            Tuple of (within_limits, usage_percentage)
        """
        subscription = self.get_active_subscription(db, user_id)
        plan_id = subscription.plan_id if subscription else "free"
        plan = SUBSCRIPTION_PLANS[plan_id]
        
        limit = plan["limits"].get(metric, 0)
        if limit == -1:  # Unlimited
            return True, 0.0
        
        usage = self.get_current_usage(db, user_id)
        if not usage:
            return True, 0.0
        
        current_value = getattr(usage, metric, 0)
        usage_percentage = (current_value / limit) * 100 if limit > 0 else 0
        
        return current_value < limit, usage_percentage
    
    def cancel_user_subscription(self, db: Session, user_id: str, immediate: bool = False) -> Dict[str, Any]:
        """Cancel user's subscription."""
        subscription = self.get_active_subscription(db, user_id)
        
        if not subscription:
            raise ValueError("No active subscription found")
        
        if immediate:
            subscription.status = SubscriptionStatus.CANCELLED.value
            subscription.cancelled_at = datetime.utcnow()
        else:
            # Cancel at end of current period
            subscription.auto_renew = False
        
        db.commit()
        
        return {
            "id": subscription.id,
            "status": subscription.status,
            "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
            "auto_renew": subscription.auto_renew
        }
    
    def initialize_usage_tracking(self, db: Session, user_id: str, subscription_id: str) -> None:
        """Initialize usage tracking for a new subscription."""
        current_time = datetime.utcnow()
        subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
        
        usage = Usage(
            id=str(uuid.uuid4()),
            user_id=user_id,
            subscription_id=subscription_id,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            users_count=1  # Initialize with 1 user
        )
        
        db.add(usage)
        db.commit()
    
    def check_usage_alerts(self, db: Session, user_id: str, usage: Usage) -> None:
        """Check and send usage alerts if thresholds are exceeded."""
        subscription = self.get_active_subscription(db, user_id)
        if not subscription:
            return
        
        plan = SUBSCRIPTION_PLANS[subscription.plan_id]
        threshold = USAGE_TRACKING["usage_alert_threshold"]
        
        for metric, limit in plan["limits"].items():
            if limit > 0:  # Skip unlimited limits
                current_value = getattr(usage, metric, 0)
                usage_percentage = current_value / limit
                
                if usage_percentage >= threshold:
                    self.send_usage_alert(user_id, metric, usage_percentage, limit)
    
    def send_usage_alert(self, user_id: str, metric: str, usage_percentage: float, limit: int) -> None:
        """Send usage alert to user."""
        # Implementation for sending alerts (email, notification, etc.)
        self.logger.warning(
            f"Usage alert for user {user_id}: {metric} at {usage_percentage:.1%} of limit ({limit})"
        )
    
    def verify_razorpay_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Razorpay webhook signature."""
        try:
            expected_signature = hmac.new(
                PAYMENT_GATEWAYS["razorpay"]["webhook_secret"].encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception:
            return False
    
    def handle_razorpay_webhook(self, event: Dict[str, Any]) -> None:
        """Handle Razorpay webhook events."""
        event_type = event.get("event")
        
        if event_type == "payment.captured":
            self.handle_payment_success(event["payload"]["payment"]["entity"], "razorpay")
        elif event_type == "payment.failed":
            self.handle_payment_failure(event["payload"]["payment"]["entity"], "razorpay")
        elif event_type == "subscription.charged":
            self.handle_subscription_renewal(event["payload"]["subscription"]["entity"], "razorpay")
    
    def handle_stripe_webhook(self, event: Dict[str, Any]) -> None:
        """Handle Stripe webhook events."""
        event_type = event["type"]
        
        if event_type == "payment_intent.succeeded":
            self.handle_payment_success(event["data"]["object"], "stripe")
        elif event_type == "payment_intent.payment_failed":
            self.handle_payment_failure(event["data"]["object"], "stripe")
        elif event_type == "invoice.payment_succeeded":
            self.handle_subscription_renewal(event["data"]["object"], "stripe")
    
    def handle_payment_success(self, payment_data: Dict[str, Any], gateway: str) -> None:
        """Handle successful payment."""
        with self.SessionLocal() as db:
            # Update payment record
            # Implementation depends on payment data structure
            pass
    
    def handle_payment_failure(self, payment_data: Dict[str, Any], gateway: str) -> None:
        """Handle failed payment."""
        with self.SessionLocal() as db:
            # Update payment record and subscription status
            # Implementation depends on payment data structure
            pass
    
    def handle_subscription_renewal(self, subscription_data: Dict[str, Any], gateway: str) -> None:
        """Handle subscription renewal."""
        with self.SessionLocal() as db:
            # Update subscription period and create new usage tracking
            # Implementation depends on subscription data structure
            pass
    
    def run(self, host='0.0.0.0', port=5001, debug=False):
        """Run the subscription management application."""
        self.app.run(host=host, port=port, debug=debug)


# Create a global instance
subscription_manager = SubscriptionManager()

