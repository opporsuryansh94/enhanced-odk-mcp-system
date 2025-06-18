# Enhanced ODK MCP System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18.0+-blue.svg)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-13+-blue.svg)](https://www.postgresql.org/)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/opporsuryansh94/enhanced-odk-mcp-system)

## 🌟 Overview

The Enhanced ODK MCP System is a comprehensive, production-ready data collection and analysis platform designed specifically for NGOs, think tanks, CSR firms, and research organizations. Built on the Model Context Protocol (MCP) architecture, it provides a scalable, secure, and intelligent solution for modern data collection needs.

### 🎯 Key Features

- **🤖 AI-Powered Intelligence**: Advanced anomaly detection, automatic insights, and smart recommendations
- **🎨 Smart Form Builder**: Drag-and-drop interface with AI-powered field suggestions
- **💳 SaaS Monetization**: Complete subscription system with tiered pricing and payment processing
- **🔒 Enterprise Security**: Multi-factor authentication, field-level encryption, and GDPR compliance
- **📊 Advanced Analytics**: Real-time dashboards, cross-project comparisons, and statistical analysis
- **📱 Mobile Excellence**: Feature-rich React Native app with offline capabilities
- **🔗 API Integration**: Comprehensive REST APIs with webhooks and third-party integrations
- **🤖 Virtual Assistant**: RAG-based chatbot for intelligent user guidance
- **🌐 Multi-Database Support**: PostgreSQL, SQLite, and Baserow integration

## 🏗️ Architecture

The system follows a microservices architecture with the following core components:

### MCP Services
- **Form Management Service** (Port 5001): Form creation, validation, and lifecycle management
- **Data Collection Service** (Port 5002): Submission handling and data processing
- **Data Aggregation Service** (Port 5003): Analytics and reporting engine

### Enhanced Services
- **Cross-Project Analytics** (Port 5004): Statistical analysis and project comparisons
- **Admin System** (Port 5005): Comprehensive administrative control panel
- **Subscription System** (Port 5006): SaaS monetization and billing management

### Frontend Applications
- **React Web Application**: Modern, responsive web interface
- **React Native Mobile App**: Feature-rich mobile application with offline support
- **Admin Dashboard**: Administrative control panel

### AI Modules
- **Anomaly Detection**: Real-time data quality monitoring
- **Data Insights**: Automatic pattern recognition and insights generation
- **Form Recommendations**: AI-powered form optimization suggestions
- **Virtual Assistant**: RAG-based user support system

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 13+ (recommended) or SQLite
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/opporsuryansh94/enhanced-odk-mcp-system.git
   cd enhanced-odk-mcp-system
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up the database**
   ```bash
   # For PostgreSQL (recommended)
   python scripts/postgresql_migration.py
   
   # For SQLite (development)
   python scripts/setup_sqlite.py
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start the services**
   ```bash
   # Start all MCP services
   python scripts/start_services.py
   
   # Or start individual services
   python mcps/form_management/src/main.py
   python mcps/data_collection/src/main.py
   python mcps/data_aggregation/src/main.py
   ```

6. **Start the web application**
   ```bash
   cd web-app
   npm install
   npm run dev
   ```

7. **Access the application**
   - Web Interface: http://localhost:3000
   - Admin Panel: http://localhost:3000/admin
   - API Documentation: http://localhost:5000/docs

### Default Credentials

- **Admin Account**: admin@odk.com / admin123
- **Demo User**: user@odk.com / user123

## 📱 Mobile Application

The React Native mobile application provides full offline capabilities and is available for both Android and iOS platforms.

### Features
- **Offline Data Collection**: Complete form filling without internet connection
- **Automatic Sync**: Data synchronization when connection is restored
- **QR Code Scanner**: Quick form access via QR codes
- **Geolocation Support**: GPS coordinates for field data collection
- **Media Capture**: Photo, video, and audio recording
- **Push Notifications**: Real-time updates and alerts

### Building the Mobile App

```bash
cd mobile-app

# Install dependencies
npm install

# For Android
npm run android

# For iOS
npm run ios

# Build release version
npm run build:android
npm run build:ios
```

## 💳 Subscription Plans

The system offers flexible pricing plans designed for different organization types:

### Plan Comparison

| Feature | Free | Starter | Professional | Enterprise |
|---------|------|---------|--------------|------------|
| **Price (Monthly)** | $0 | $29 | $99 | $299 |
| **Price (Yearly)** | $0 | $290 | $990 | $2,990 |
| **Forms** | 3 | 25 | Unlimited | Unlimited |
| **Submissions/Month** | 100 | 1,000 | 10,000 | Unlimited |
| **Users** | 2 | 5 | 25 | Unlimited |
| **Storage** | 1GB | 10GB | 100GB | Unlimited |
| **API Calls/Month** | 1,000 | 10,000 | 100,000 | Unlimited |
| **Analytics** | Basic | Advanced | Advanced + AI | Advanced + AI |
| **Support** | Email | Priority Email | Phone + Email | Dedicated Manager |
| **Integrations** | Basic | Basic | All | Custom |

### Organization Discounts

- **NGOs**: 50% discount on all plans
- **Academic Institutions**: 40% discount
- **Government Organizations**: 30% discount
- **Startups**: 25% discount
- **Corporate**: Standard pricing

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database Configuration
DATABASE_TYPE=postgresql  # postgresql, sqlite, baserow
DATABASE_URL=postgresql://user:password@localhost:5432/odk_mcp

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here

# Payment Gateways
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=test_secret_...

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# AI Services
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Storage
STORAGE_TYPE=local  # local, s3, gcs
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_S3_BUCKET=your-bucket-name
```

### Database Configuration

The system supports multiple database backends:

#### PostgreSQL (Recommended)
```python
DATABASE_CONFIG = {
    'type': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'database': 'odk_mcp',
    'username': 'postgres',
    'password': 'password'
}
```

#### SQLite (Development)
```python
DATABASE_CONFIG = {
    'type': 'sqlite',
    'path': 'data/odk_mcp.db'
}
```

#### Baserow Integration
```python
DATABASE_CONFIG = {
    'type': 'baserow',
    'api_url': 'https://api.baserow.io',
    'api_token': 'your-baserow-token',
    'database_id': 'your-database-id'
}
```

## 🔐 Security Features

### Authentication & Authorization
- **Multi-Factor Authentication (2FA)**: TOTP-based 2FA support
- **Role-Based Access Control (RBAC)**: Granular permissions system
- **JWT Token Authentication**: Secure API access
- **Session Management**: Secure session handling with automatic expiry

### Data Protection
- **Field-Level Encryption**: Sensitive data encryption at rest
- **Data in Transit**: TLS 1.3 encryption for all communications
- **GDPR Compliance**: Data privacy and user rights management
- **Audit Trails**: Comprehensive logging for compliance

### Security Best Practices
- **Input Validation**: Comprehensive data validation and sanitization
- **SQL Injection Prevention**: Parameterized queries and ORM usage
- **XSS Protection**: Content Security Policy and output encoding
- **Rate Limiting**: API rate limiting and DDoS protection

## 📊 Analytics & Reporting

### Built-in Analytics
- **Real-time Dashboards**: Live data visualization with Plotly and D3.js
- **Statistical Analysis**: Descriptive and inferential statistics
- **Geospatial Mapping**: Interactive maps with data overlays
- **Cross-Project Comparisons**: Statistical analysis across multiple projects

### AI-Powered Insights
- **Anomaly Detection**: Automatic identification of data quality issues
- **Pattern Recognition**: Machine learning-based trend analysis
- **Predictive Analytics**: Forecasting and trend prediction
- **Automated Reporting**: AI-generated insights and recommendations

### Export Capabilities
- **PDF Reports**: Professional report generation
- **Excel Export**: Data export in multiple formats
- **API Access**: Programmatic data access
- **Webhook Integration**: Real-time data streaming

## 🔗 API Documentation

### Core Endpoints

#### Authentication
```http
POST /auth/login
POST /auth/register
POST /auth/logout
GET /auth/profile
```

#### Form Management
```http
GET /forms
POST /forms
GET /forms/{id}
PUT /forms/{id}
DELETE /forms/{id}
```

#### Data Collection
```http
GET /submissions
POST /submissions
GET /submissions/{id}
PUT /submissions/{id}
DELETE /submissions/{id}
```

#### Analytics
```http
GET /analytics/dashboard
GET /analytics/reports
POST /analytics/comparisons
GET /analytics/insights
```

#### Admin
```http
GET /admin/users
POST /admin/users/{id}/suspend
GET /admin/settings
POST /admin/settings
GET /admin/audit-logs
```

#### Subscriptions
```http
GET /subscriptions/plans
GET /subscriptions
POST /subscriptions
PUT /subscriptions/{id}
DELETE /subscriptions/{id}
```

### Webhook Events

The system supports webhooks for real-time integrations:

- `form.created`
- `form.updated`
- `submission.created`
- `submission.updated`
- `user.registered`
- `subscription.created`
- `payment.succeeded`
- `payment.failed`

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/e2e/

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Service integration testing
- **End-to-End Tests**: Complete workflow testing
- **Performance Tests**: Load and stress testing
- **Security Tests**: Vulnerability and penetration testing

## 🚀 Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Scale services
docker-compose up -d --scale form-management=3
```

### Cloud Deployment

#### AWS
```bash
# Deploy to AWS ECS
aws ecs create-cluster --cluster-name odk-mcp-cluster
aws ecs create-service --cluster odk-mcp-cluster --service-name odk-mcp-service
```

#### Google Cloud
```bash
# Deploy to Google Cloud Run
gcloud run deploy odk-mcp-system --source .
```

#### Azure
```bash
# Deploy to Azure Container Instances
az container create --resource-group odk-mcp-rg --name odk-mcp-container
```

### Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL certificates installed
- [ ] Monitoring and logging configured
- [ ] Backup strategy implemented
- [ ] Security scanning completed
- [ ] Performance testing passed
- [ ] Documentation updated

## 🤝 Contributing

We welcome contributions from the community! Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and contribute to the project.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Standards

- Follow PEP 8 for Python code
- Use ESLint and Prettier for JavaScript/React code
- Write comprehensive tests for new features
- Update documentation for API changes
- Follow semantic versioning for releases

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- [User Manual](docs/user_manual_complete.pdf)
- [API Documentation](docs/api_documentation_complete.pdf)
- [Mobile App Guide](docs/mobile_app_guide_complete.pdf)
- [Deployment Guide](docs/deployment_operations_manual.pdf)

### Community Support
- [GitHub Issues](https://github.com/opporsuryansh94/enhanced-odk-mcp-system/issues)
- [Discussions](https://github.com/opporsuryansh94/enhanced-odk-mcp-system/discussions)
- [Wiki](https://github.com/opporsuryansh94/enhanced-odk-mcp-system/wiki)

### Professional Support
For enterprise customers, we offer:
- Dedicated support manager
- Priority issue resolution
- Custom feature development
- Training and onboarding
- SLA guarantees

Contact: support@odk-mcp.com

## 🙏 Acknowledgments

- [Open Data Kit](https://getodk.org/) for the foundational concepts
- [Model Context Protocol](https://modelcontextprotocol.io/) for the architecture framework
- All contributors and community members
- Organizations using the system for social impact

---

**Built with ❤️ by the ODK MCP System Team**

For more information, visit our [website](https://odk-mcp.com) or follow us on [Twitter](https://twitter.com/odk_mcp).

