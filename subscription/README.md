# Subscription-Based Access Control for ODK MCP System

This directory contains the subscription management system for the ODK MCP System, enabling tiered pricing and access control based on subscription plans.

## Directory Structure

- `api/`: RESTful API endpoints for subscription management
- `models/`: Database models for subscription plans, billing, and usage tracking
- `services/`: Business logic for subscription management
- `payment_gateways/`: Integration with payment processors (Stripe, Razorpay)
- `utils/`: Utility functions for subscription management

## Features

- Subscription plan management (creation, modification, deletion)
- User subscription management (subscribe, upgrade, downgrade, cancel)
- Usage tracking and limits enforcement
- Billing and invoice management
- Payment processing via Stripe or Razorpay

## Subscription Plans

The system supports the following subscription tiers:

1. **Free Tier**:
   - Limited forms (5)
   - Limited submissions per month (100)
   - Basic analytics
   - No API access

2. **Starter Tier**:
   - Up to 20 forms
   - Up to 1,000 submissions per month
   - Basic analytics
   - Limited API access

3. **Pro Tier**:
   - Up to 100 forms
   - Up to 10,000 submissions per month
   - Advanced analytics
   - Full API access
   - Priority support

4. **Enterprise Tier**:
   - Unlimited forms
   - Unlimited submissions
   - Advanced analytics with custom reports
   - Full API access with higher rate limits
   - Dedicated support
   - Custom branding options

## Integration Points

The subscription system integrates with other components of the ODK MCP System:

1. **User Authentication**: To associate subscriptions with user accounts
2. **Form Management**: To enforce form count limits
3. **Data Collection**: To enforce submission limits
4. **Data Analysis**: To control access to advanced analytics features
5. **API Gateway**: To enforce API rate limits based on subscription tier

## Configuration

Subscription system configuration is stored in `config.py`. This includes:

- Payment gateway credentials
- Subscription plan definitions
- Rate limits for each tier
- Feature flags for each tier

