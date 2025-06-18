# Form Management MCP Service

## Overview

The Form Management MCP Service is a core component of the Enhanced ODK MCP System, responsible for handling all aspects of form creation, validation, management, and lifecycle operations. Built on the Model Context Protocol framework, this service provides a robust, scalable solution for dynamic form management with AI-powered enhancements.

## Architecture

### Service Design

The Form Management Service follows a microservices architecture pattern with clear separation of concerns:

- **API Layer**: RESTful endpoints for form operations
- **Business Logic Layer**: Form validation, processing, and AI integration
- **Data Access Layer**: PostgreSQL integration with optimized queries
- **AI Integration Layer**: Smart form suggestions and optimization

### Database Schema

**Forms Table**
```sql
CREATE TABLE forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1,
    status form_status DEFAULT 'draft',
    fields JSONB NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id)
);
```

**Form Templates Table**
```sql
CREATE TABLE form_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    template_data JSONB NOT NULL,
    is_public BOOLEAN DEFAULT false,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## API Endpoints

### Authentication

All endpoints require authentication via JWT token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

### Form Operations

#### Create Form
```http
POST /api/forms
Content-Type: application/json

{
  "title": "Community Health Survey",
  "description": "Quarterly health assessment for rural communities",
  "fields": [
    {
      "name": "respondent_age",
      "type": "number",
      "label": "Age of Respondent",
      "required": true,
      "validation": {
        "min": 0,
        "max": 120
      }
    },
    {
      "name": "health_status",
      "type": "select",
      "label": "Overall Health Status",
      "required": true,
      "options": [
        {"value": "excellent", "label": "Excellent"},
        {"value": "good", "label": "Good"},
        {"value": "fair", "label": "Fair"},
        {"value": "poor", "label": "Poor"}
      ]
    }
  ],
  "settings": {
    "allow_multiple_submissions": true,
    "require_authentication": false,
    "enable_geolocation": true
  }
}
```

**Response**
```json
{
  "id": "form_123",
  "title": "Community Health Survey",
  "status": "draft",
  "version": 1,
  "created_at": "2024-12-06T10:30:00Z",
  "qr_code_url": "https://api.yourdomain.com/qr/form_123"
}
```

#### List Forms
```http
GET /api/forms?page=1&limit=20&search=health&status=active
```

**Response**
```json
{
  "forms": [
    {
      "id": "form_123",
      "title": "Community Health Survey",
      "description": "Quarterly health assessment",
      "status": "active",
      "version": 2,
      "submission_count": 1247,
      "created_at": "2024-12-06T10:30:00Z",
      "updated_at": "2024-12-06T15:45:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 45,
    "pages": 3
  }
}
```

#### Get Form Details
```http
GET /api/forms/{form_id}
```

#### Update Form
```http
PUT /api/forms/{form_id}
Content-Type: application/json

{
  "title": "Updated Community Health Survey",
  "fields": [...],
  "settings": {...}
}
```

#### Delete Form
```http
DELETE /api/forms/{form_id}
```

#### Publish Form
```http
POST /api/forms/{form_id}/publish
```

### Form Templates

#### List Templates
```http
GET /api/templates?category=health&public=true
```

#### Create Template from Form
```http
POST /api/forms/{form_id}/create-template
Content-Type: application/json

{
  "name": "Health Survey Template",
  "category": "health",
  "description": "Standard health assessment template",
  "is_public": false
}
```

### AI-Powered Features

#### Get Field Suggestions
```http
POST /api/forms/ai/suggest-fields
Content-Type: application/json

{
  "context": "health survey for rural communities",
  "existing_fields": ["age", "gender"],
  "target_audience": "rural_population"
}
```

**Response**
```json
{
  "suggestions": [
    {
      "name": "household_size",
      "type": "number",
      "label": "Number of people in household",
      "confidence": 0.92,
      "reasoning": "Household size is commonly collected in rural health surveys for demographic analysis"
    },
    {
      "name": "water_source",
      "type": "select",
      "label": "Primary water source",
      "options": [
        {"value": "well", "label": "Well"},
        {"value": "river", "label": "River/Stream"},
        {"value": "piped", "label": "Piped water"}
      ],
      "confidence": 0.88,
      "reasoning": "Water source is critical for health outcomes in rural areas"
    }
  ]
}
```

#### Analyze CSV for Form Generation
```http
POST /api/forms/ai/analyze-csv
Content-Type: multipart/form-data

file: [CSV file]
```

#### Optimize Form
```http
POST /api/forms/{form_id}/optimize
Content-Type: application/json

{
  "optimization_goals": ["completion_rate", "data_quality"],
  "target_audience": "rural_communities"
}
```

## Configuration

### Environment Variables

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=odk_mcp_forms
DB_USER=forms_user
DB_PASSWORD=secure_password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# Service Configuration
SERVICE_PORT=5001
SERVICE_HOST=0.0.0.0
DEBUG=false
LOG_LEVEL=INFO

# AI Configuration
OPENAI_API_KEY=your_openai_key
AI_MODEL=gpt-4
AI_TEMPERATURE=0.7
MAX_SUGGESTIONS=5

# File Storage
UPLOAD_FOLDER=/var/uploads/forms
MAX_FILE_SIZE=10MB
ALLOWED_EXTENSIONS=csv,xlsx,json

# Security
JWT_SECRET_KEY=your_jwt_secret
BCRYPT_LOG_ROUNDS=12
RATE_LIMIT_PER_MINUTE=100
```

### Database Setup

```bash
# Create database
createdb odk_mcp_forms

# Run migrations
python src/migrations/create_tables.py

# Seed initial data
python src/migrations/seed_templates.py
```

## Development

### Local Setup

```bash
# Clone repository
git clone https://github.com/opporsuryansh94/enhanced-odk-mcp-system.git
cd enhanced-odk-mcp-system/mcps/form_management

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
python src/migrations/create_tables.py

# Start the service
python src/main.py
```

### Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test categories
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
```

### API Testing

```bash
# Test form creation
curl -X POST http://localhost:5001/api/forms \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "title": "Test Form",
    "fields": [
      {
        "name": "test_field",
        "type": "text",
        "label": "Test Field",
        "required": true
      }
    ]
  }'

# Test form listing
curl -X GET http://localhost:5001/api/forms \
  -H "Authorization: Bearer $JWT_TOKEN"
```

## Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY migrations/ ./migrations/

EXPOSE 5000

CMD ["python", "src/main.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  form-management:
    build: .
    ports:
      - "5001:5000"
    environment:
      - DB_HOST=postgres
      - REDIS_HOST=redis
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: odk_mcp_forms
      POSTGRES_USER: forms_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass redis_password
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Production Considerations

**Performance Optimization**
- Enable database connection pooling
- Implement Redis caching for frequently accessed forms
- Use CDN for static assets and form templates
- Enable gzip compression for API responses

**Security Hardening**
- Implement rate limiting per user/IP
- Enable CORS with specific allowed origins
- Use HTTPS in production with proper SSL certificates
- Implement input validation and sanitization
- Enable audit logging for all form operations

**Monitoring and Logging**
- Set up application performance monitoring (APM)
- Configure structured logging with correlation IDs
- Implement health checks and metrics endpoints
- Set up alerts for error rates and response times

## Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Check database connectivity
pg_isready -h $DB_HOST -p $DB_PORT

# Verify credentials
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME
```

**Redis Connection Issues**
```bash
# Test Redis connectivity
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping

# Check Redis authentication
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping
```

**AI Service Errors**
- Verify OpenAI API key is valid and has sufficient credits
- Check rate limits and quota usage
- Ensure proper network connectivity to AI services

### Performance Issues

**Slow Form Loading**
- Check database query performance with EXPLAIN ANALYZE
- Verify proper indexing on frequently queried columns
- Consider implementing form caching with Redis

**High Memory Usage**
- Monitor memory usage with system tools
- Check for memory leaks in long-running processes
- Optimize database queries to reduce memory footprint

### Debugging

**Enable Debug Mode**
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python src/main.py
```

**Database Query Logging**
```python
# Add to configuration
SQLALCHEMY_ECHO = True
```

**API Request Logging**
```python
# Enable request logging middleware
app.config['LOG_REQUESTS'] = True
```

## Contributing

We welcome contributions to the Form Management Service! Please see the main project [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

### Development Guidelines

**Code Style**
- Follow PEP 8 for Python code
- Use type hints for all function parameters and return values
- Write comprehensive docstrings for all public methods
- Maintain test coverage above 90%

**Testing Requirements**
- Write unit tests for all business logic
- Include integration tests for API endpoints
- Add performance tests for critical operations
- Test error handling and edge cases

**Documentation**
- Update API documentation for any endpoint changes
- Include examples in docstrings
- Update this README for any configuration changes
- Add inline comments for complex business logic

## License

This service is part of the Enhanced ODK MCP System and is licensed under the MIT License. See the main project [LICENSE](../../LICENSE) file for details.

