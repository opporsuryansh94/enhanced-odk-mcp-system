"""
Enhanced Subscription and Pricing Service for ODK MCP System
Comprehensive SaaS monetization with tiered pricing and payment processing
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
import stripe
import razorpay
from decimal import Decimal

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
db_manager = get_database_manager('subscription_system')
app.config['SQLALCHEMY_DATABASE_URI'] = db_manager.config.get_sqlalchemy_url()

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Payment gateway configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_...')
razorpay_client = razorpay.Client(
    auth=(
        os.getenv('RAZORPAY_KEY_ID', 'rzp_test_...'),
        os.getenv('RAZORPAY_KEY_SECRET', 'test_secret_...')
    )
)

# Subscription Models
class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Pricing
    price_monthly = db.Column(db.Numeric(10, 2), nullable=False)
    price_yearly = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # Limits and features
    features = db.Column(db.JSON, nullable=False)
    limits = db.Column(db.JSON, nullable=False)
    
    # Organization types
    target_organizations = db.Column(db.JSON, default=lambda: ['all'])  # ngo, corporate, government, academic, startup
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_popular = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'price_monthly': float(self.price_monthly),
            'price_yearly': float(self.price_yearly),
            'currency': self.currency,
            'features': self.features,
            'limits': self.limits,
            'target_organizations': self.target_organizations,
            'is_active': self.is_active,
            'is_popular': self.is_popular,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class OrganizationSubscription(db.Model):
    __tablename__ = 'organization_subscriptions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(db.String(36), nullable=False)
    plan_id = db.Column(db.String(36), db.ForeignKey('subscription_plans.id'), nullable=False)
    
    # Subscription details
    status = db.Column(db.String(20), default='active')  # active, cancelled, expired, suspended
    billing_cycle = db.Column(db.String(10), default='monthly')  # monthly, yearly
    
    # Dates
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    trial_end_date = db.Column(db.DateTime)
    
    # Payment
    payment_method = db.Column(db.String(20))  # stripe, razorpay, manual
    external_subscription_id = db.Column(db.String(100))  # Stripe/Razorpay subscription ID
    
    # Usage tracking
    current_usage = db.Column(db.JSON, default=lambda: {})
    usage_alerts_sent = db.Column(db.JSON, default=lambda: [])
    
    # Billing
    next_billing_date = db.Column(db.DateTime)
    last_billing_date = db.Column(db.DateTime)
    auto_renew = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    plan = db.relationship('SubscriptionPlan', backref='subscriptions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'plan_id': self.plan_id,
            'plan': self.plan.to_dict() if self.plan else None,
            'status': self.status,
            'billing_cycle': self.billing_cycle,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'trial_end_date': self.trial_end_date.isoformat() if self.trial_end_date else None,
            'payment_method': self.payment_method,
            'external_subscription_id': self.external_subscription_id,
            'current_usage': self.current_usage,
            'next_billing_date': self.next_billing_date.isoformat() if self.next_billing_date else None,
            'last_billing_date': self.last_billing_date.isoformat() if self.last_billing_date else None,
            'auto_renew': self.auto_renew,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class UsageRecord(db.Model):
    __tablename__ = 'usage_records'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(db.String(36), nullable=False)
    subscription_id = db.Column(db.String(36), db.ForeignKey('organization_subscriptions.id'), nullable=False)
    
    # Usage details
    metric = db.Column(db.String(50), nullable=False)  # forms, submissions, storage, api_calls, users
    quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(20), default='count')  # count, bytes, minutes
    
    # Metadata
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    
    # Additional context
    resource_id = db.Column(db.String(36))  # ID of the specific resource (form, project, etc.)
    metadata = db.Column(db.JSON, default=lambda: {})
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'subscription_id': self.subscription_id,
            'metric': self.metric,
            'quantity': self.quantity,
            'unit': self.unit,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'resource_id': self.resource_id,
            'metadata': self.metadata
        }

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = db.Column(db.String(36), nullable=False)
    subscription_id = db.Column(db.String(36), db.ForeignKey('organization_subscriptions.id'), nullable=False)
    
    # Invoice details
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, paid, failed, cancelled
    
    # Amounts
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # Dates
    issue_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    due_date = db.Column(db.DateTime, nullable=False)
    paid_date = db.Column(db.DateTime)
    
    # Payment
    payment_method = db.Column(db.String(20))
    payment_reference = db.Column(db.String(100))
    
    # Line items
    line_items = db.Column(db.JSON, nullable=False)
    
    # Files
    pdf_path = db.Column(db.String(500))
    
    def to_dict(self):
        return {
            'id': self.id,
            'organization_id': self.organization_id,
            'subscription_id': self.subscription_id,
            'invoice_number': self.invoice_number,
            'status': self.status,
            'subtotal': float(self.subtotal),
            'tax_amount': float(self.tax_amount),
            'discount_amount': float(self.discount_amount),
            'total_amount': float(self.total_amount),
            'currency': self.currency,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
            'line_items': self.line_items,
            'pdf_path': self.pdf_path
        }

# Authentication middleware
@app.before_request
def authenticate_request():
    """Authenticate requests"""
    
    # Skip authentication for health check and webhooks
    if request.endpoint in ['health', 'stripe_webhook', 'razorpay_webhook']:
        return
    
    # Get authentication token
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Store user info in g for request context
    g.user_id = request.headers.get('X-User-ID', 'anonymous')
    g.organization_id = request.headers.get('X-Organization-ID', 'default')

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'service': 'subscription_system',
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

# Subscription plan endpoints
@app.route('/plans', methods=['GET'])
def list_plans():
    """List available subscription plans"""
    try:
        org_type = request.args.get('org_type', 'all')
        
        query = SubscriptionPlan.query.filter_by(is_active=True)
        
        if org_type != 'all':
            query = query.filter(
                db.or_(
                    SubscriptionPlan.target_organizations.contains([org_type]),
                    SubscriptionPlan.target_organizations.contains(['all'])
                )
            )
        
        plans = query.order_by(SubscriptionPlan.sort_order).all()
        
        return jsonify({
            'plans': [plan.to_dict() for plan in plans]
        })
        
    except Exception as e:
        logger.error(f"Error listing plans: {str(e)}")
        return jsonify({'error': 'Failed to list plans'}), 500

@app.route('/plans/<plan_id>/pricing', methods=['GET'])
def get_plan_pricing(plan_id):
    """Get detailed pricing for a specific plan"""
    try:
        plan = SubscriptionPlan.query.filter_by(id=plan_id, is_active=True).first()
        if not plan:
            return jsonify({'error': 'Plan not found'}), 404
        
        org_type = request.args.get('org_type', 'corporate')
        billing_cycle = request.args.get('billing_cycle', 'monthly')
        
        # Calculate pricing with discounts
        base_price = plan.price_monthly if billing_cycle == 'monthly' else plan.price_yearly
        
        # Apply organization type discounts
        discount_percentage = get_organization_discount(org_type)
        discounted_price = base_price * (1 - discount_percentage / 100)
        
        # Calculate savings for yearly billing
        yearly_savings = 0
        if billing_cycle == 'yearly':
            monthly_total = plan.price_monthly * 12
            yearly_savings = float(monthly_total - plan.price_yearly)
        
        pricing = {
            'plan': plan.to_dict(),
            'billing_cycle': billing_cycle,
            'base_price': float(base_price),
            'discount_percentage': discount_percentage,
            'discounted_price': float(discounted_price),
            'final_price': float(discounted_price),
            'currency': plan.currency,
            'yearly_savings': yearly_savings,
            'organization_type': org_type
        }
        
        return jsonify(pricing)
        
    except Exception as e:
        logger.error(f"Error getting plan pricing: {str(e)}")
        return jsonify({'error': 'Failed to get plan pricing'}), 500

def get_organization_discount(org_type):
    """Get discount percentage based on organization type"""
    discounts = {
        'ngo': 50,          # 50% discount for NGOs
        'academic': 40,     # 40% discount for academic institutions
        'government': 30,   # 30% discount for government organizations
        'startup': 25,      # 25% discount for startups
        'corporate': 0      # No discount for corporate
    }
    return discounts.get(org_type, 0)

# Subscription management endpoints
@app.route('/subscriptions', methods=['GET'])
def get_subscription():
    """Get current subscription for organization"""
    try:
        subscription = OrganizationSubscription.query.filter_by(
            organization_id=g.organization_id,
            status='active'
        ).first()
        
        if not subscription:
            return jsonify({'subscription': None})
        
        # Get current usage
        current_usage = get_current_usage(subscription.id)
        subscription.current_usage = current_usage
        
        return jsonify({
            'subscription': subscription.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting subscription: {str(e)}")
        return jsonify({'error': 'Failed to get subscription'}), 500

@app.route('/subscriptions', methods=['POST'])
def create_subscription():
    """Create a new subscription"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['plan_id', 'billing_cycle', 'payment_method']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        plan = SubscriptionPlan.query.filter_by(id=data['plan_id'], is_active=True).first()
        if not plan:
            return jsonify({'error': 'Invalid plan'}), 400
        
        # Check for existing active subscription
        existing = OrganizationSubscription.query.filter_by(
            organization_id=g.organization_id,
            status='active'
        ).first()
        
        if existing:
            return jsonify({'error': 'Organization already has an active subscription'}), 400
        
        # Calculate subscription dates
        start_date = datetime.now(timezone.utc)
        if data['billing_cycle'] == 'yearly':
            end_date = start_date + timedelta(days=365)
        else:
            end_date = start_date + timedelta(days=30)
        
        # Create subscription
        subscription = OrganizationSubscription(
            organization_id=g.organization_id,
            plan_id=data['plan_id'],
            billing_cycle=data['billing_cycle'],
            start_date=start_date,
            end_date=end_date,
            payment_method=data['payment_method'],
            next_billing_date=end_date
        )
        
        # Add trial period if applicable
        if data.get('trial_days', 0) > 0:
            subscription.trial_end_date = start_date + timedelta(days=data['trial_days'])
        
        db.session.add(subscription)
        db.session.commit()
        
        # Process payment
        if data['payment_method'] in ['stripe', 'razorpay']:
            payment_result = process_subscription_payment(subscription, data)
            if not payment_result['success']:
                db.session.delete(subscription)
                db.session.commit()
                return jsonify({'error': payment_result['error']}), 400
            
            subscription.external_subscription_id = payment_result['subscription_id']
            db.session.commit()
        
        logger.info(f"Subscription created: {subscription.id}")
        
        return jsonify({
            'message': 'Subscription created successfully',
            'subscription': subscription.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating subscription: {str(e)}")
        return jsonify({'error': 'Failed to create subscription'}), 500

def process_subscription_payment(subscription, payment_data):
    """Process payment for subscription"""
    try:
        if payment_data['payment_method'] == 'stripe':
            return process_stripe_payment(subscription, payment_data)
        elif payment_data['payment_method'] == 'razorpay':
            return process_razorpay_payment(subscription, payment_data)
        else:
            return {'success': False, 'error': 'Invalid payment method'}
    
    except Exception as e:
        logger.error(f"Payment processing failed: {str(e)}")
        return {'success': False, 'error': 'Payment processing failed'}

def process_stripe_payment(subscription, payment_data):
    """Process Stripe payment"""
    try:
        # Create Stripe customer
        customer = stripe.Customer.create(
            email=payment_data.get('email'),
            metadata={'organization_id': subscription.organization_id}
        )
        
        # Create Stripe subscription
        stripe_subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{
                'price_data': {
                    'currency': subscription.plan.currency.lower(),
                    'product_data': {
                        'name': subscription.plan.display_name,
                    },
                    'unit_amount': int(float(subscription.plan.price_monthly) * 100),
                    'recurring': {
                        'interval': 'month' if subscription.billing_cycle == 'monthly' else 'year',
                    },
                },
            }],
            payment_behavior='default_incomplete',
            expand=['latest_invoice.payment_intent'],
        )
        
        return {
            'success': True,
            'subscription_id': stripe_subscription.id,
            'client_secret': stripe_subscription.latest_invoice.payment_intent.client_secret
        }
        
    except Exception as e:
        logger.error(f"Stripe payment failed: {str(e)}")
        return {'success': False, 'error': str(e)}

def process_razorpay_payment(subscription, payment_data):
    """Process Razorpay payment"""
    try:
        # Create Razorpay subscription
        razorpay_subscription = razorpay_client.subscription.create({
            'plan_id': f"plan_{subscription.plan.name}_{subscription.billing_cycle}",
            'customer_notify': 1,
            'total_count': 12 if subscription.billing_cycle == 'monthly' else 1,
            'notes': {
                'organization_id': subscription.organization_id,
                'subscription_id': subscription.id
            }
        })
        
        return {
            'success': True,
            'subscription_id': razorpay_subscription['id']
        }
        
    except Exception as e:
        logger.error(f"Razorpay payment failed: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_current_usage(subscription_id):
    """Get current usage for subscription"""
    try:
        # Get usage for current billing period
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        usage_records = UsageRecord.query.filter(
            UsageRecord.subscription_id == subscription_id,
            UsageRecord.period_start >= start_of_month
        ).all()
        
        # Aggregate usage by metric
        usage = {}
        for record in usage_records:
            if record.metric not in usage:
                usage[record.metric] = 0
            usage[record.metric] += record.quantity
        
        return usage
        
    except Exception as e:
        logger.error(f"Error getting current usage: {str(e)}")
        return {}

# Initialize database and default plans
@app.before_first_request
def create_tables():
    """Create database tables and default subscription plans"""
    try:
        db.create_all()
        
        # Create default subscription plans if not exist
        if SubscriptionPlan.query.count() == 0:
            create_default_plans()
        
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")

def create_default_plans():
    """Create default subscription plans"""
    plans = [
        {
            'name': 'free',
            'display_name': 'Free',
            'description': 'Perfect for small organizations getting started',
            'price_monthly': Decimal('0.00'),
            'price_yearly': Decimal('0.00'),
            'features': [
                'Up to 3 forms',
                'Up to 100 submissions/month',
                'Basic analytics',
                'Email support',
                '1GB storage'
            ],
            'limits': {
                'forms': 3,
                'submissions_per_month': 100,
                'users': 2,
                'storage_gb': 1,
                'api_calls_per_month': 1000
            },
            'target_organizations': ['all'],
            'sort_order': 1
        },
        {
            'name': 'starter',
            'display_name': 'Starter',
            'description': 'Ideal for growing organizations',
            'price_monthly': Decimal('29.00'),
            'price_yearly': Decimal('290.00'),
            'features': [
                'Up to 25 forms',
                'Up to 1,000 submissions/month',
                'Advanced analytics',
                'Priority email support',
                '10GB storage',
                'Basic integrations'
            ],
            'limits': {
                'forms': 25,
                'submissions_per_month': 1000,
                'users': 5,
                'storage_gb': 10,
                'api_calls_per_month': 10000
            },
            'target_organizations': ['all'],
            'sort_order': 2
        },
        {
            'name': 'professional',
            'display_name': 'Professional',
            'description': 'For established organizations with advanced needs',
            'price_monthly': Decimal('99.00'),
            'price_yearly': Decimal('990.00'),
            'features': [
                'Unlimited forms',
                'Up to 10,000 submissions/month',
                'Advanced analytics & reporting',
                'Phone & email support',
                '100GB storage',
                'All integrations',
                'Custom branding',
                'API access'
            ],
            'limits': {
                'forms': -1,  # Unlimited
                'submissions_per_month': 10000,
                'users': 25,
                'storage_gb': 100,
                'api_calls_per_month': 100000
            },
            'target_organizations': ['all'],
            'is_popular': True,
            'sort_order': 3
        },
        {
            'name': 'enterprise',
            'display_name': 'Enterprise',
            'description': 'For large organizations requiring maximum capabilities',
            'price_monthly': Decimal('299.00'),
            'price_yearly': Decimal('2990.00'),
            'features': [
                'Unlimited everything',
                'Unlimited submissions',
                'Advanced analytics & AI insights',
                'Dedicated support manager',
                'Unlimited storage',
                'Custom integrations',
                'White-label solution',
                'SLA guarantee',
                'On-premise deployment option'
            ],
            'limits': {
                'forms': -1,
                'submissions_per_month': -1,
                'users': -1,
                'storage_gb': -1,
                'api_calls_per_month': -1
            },
            'target_organizations': ['all'],
            'sort_order': 4
        }
    ]
    
    for plan_data in plans:
        plan = SubscriptionPlan(**plan_data)
        db.session.add(plan)
    
    db.session.commit()
    logger.info("Default subscription plans created")

if __name__ == '__main__':
    port = int(os.getenv('SUBSCRIPTION_SYSTEM_PORT', 5006))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Subscription System service on port {port}")
    logger.info(f"Database type: {db_manager.config.database_type}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

