# Form Management MCP Service

## Overview

The Form Management MCP Service is a core component of the Enhanced ODK MCP System, responsible for form creation, validation, lifecycle management, and template handling. Built with Flask and PostgreSQL, it provides a robust foundation for dynamic form management with AI-powered features.

## Features

### Core Functionality
- **Dynamic Form Creation**: Create forms programmatically with flexible field types
- **XLSForm Support**: Import and export forms in XLSForm format
- **Form Validation**: Comprehensive validation rules and constraints
- **Version Management**: Track form versions and changes
- **Template Library**: Pre-built form templates for common use cases

### AI-Powered Features
- **Smart Field Suggestions**: AI-powered field recommendations based on form context
- **Validation Optimization**: Automatic validation rule suggestions
- **Form Analytics**: Usage patterns and completion rate analysis
- **Quality Scoring**: Automatic form quality assessment

### Advanced Capabilities
- **Multi-language Support**: Internationalization and localization
- **Conditional Logic**: Skip patterns and display conditions
- **Custom Validation**: JavaScript-based custom validation rules
- **Form Branching**: Complex form flows and routing

## API Endpoints

### Form Management
```http
GET    /forms                    # List all forms
POST   /forms                    # Create new form
GET    /forms/{id}               # Get specific form
PUT    /forms/{id}               # Update form
DELETE /forms/{id}               # Delete form
POST   /forms/{id}/publish       # Publish form
POST   /forms/{id}/unpublish     # Unpublish form
```

### Form Templates
```http
GET    /templates                # List form templates
GET    /templates/{id}           # Get specific template
POST   /forms/from-template/{id} # Create form from template
```

### Form Validation
```http
POST   /forms/{id}/validate      # Validate form structure
POST   /forms/validate-xlsform   # Validate XLSForm file
```

### AI Features
```http
POST   /forms/{id}/suggestions   # Get AI field suggestions
GET    /forms/{id}/analytics     # Get form analytics
POST   /forms/{id}/optimize      # Get optimization recommendations
```

## Configuration

### Environment Variables
```env
FORM_MANAGEMENT_PORT=5001
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:password@localhost:5432/form_management
SECRET_KEY=your-secret-key
AI_ENABLED=true
OPENAI_API_KEY=your-openai-key
```

### Database Configuration
The service supports multiple database backends through the shared database configuration:

```python
from shared.database_config import get_database_manager

db_manager = get_database_manager('form_management')
```

## Data Models

### Form Model
```python
class Form(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    version = db.Column(db.String(20), default='1.0')
    status = db.Column(db.String(20), default='draft')
    schema = db.Column(db.JSON, nullable=False)
    settings = db.Column(db.JSON, default={})
    created_by = db.Column(db.String(36), nullable=False)
    organization_id = db.Column(db.String(36), nullable=False)
    project_id = db.Column(db.String(36))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### Field Types
- **Text**: Single-line text input
- **Textarea**: Multi-line text input
- **Number**: Numeric input with validation
- **Date**: Date picker
- **Time**: Time picker
- **DateTime**: Combined date and time
- **Select**: Single selection dropdown
- **MultiSelect**: Multiple selection
- **Radio**: Radio button group
- **Checkbox**: Checkbox group
- **File**: File upload
- **Image**: Image upload with preview
- **Location**: GPS coordinates
- **Barcode**: Barcode/QR code scanner
- **Signature**: Digital signature capture

## Usage Examples

### Creating a Form
```python
import requests

form_data = {
    "title": "Customer Feedback Survey",
    "description": "Collect customer feedback and satisfaction ratings",
    "schema": {
        "fields": [
            {
                "name": "customer_name",
                "type": "text",
                "label": "Customer Name",
                "required": True
            },
            {
                "name": "satisfaction",
                "type": "select",
                "label": "Satisfaction Rating",
                "options": ["Very Satisfied", "Satisfied", "Neutral", "Dissatisfied", "Very Dissatisfied"],
                "required": True
            },
            {
                "name": "comments",
                "type": "textarea",
                "label": "Additional Comments",
                "required": False
            }
        ]
    },
    "settings": {
        "allow_multiple_submissions": True,
        "require_authentication": False,
        "notification_email": "admin@example.com"
    }
}

response = requests.post(
    "http://localhost:5001/forms",
    json=form_data,
    headers={"Authorization": "Bearer your-token"}
)
```

### Getting AI Suggestions
```python
response = requests.post(
    "http://localhost:5001/forms/form-id/suggestions",
    json={
        "context": "customer feedback survey for restaurant",
        "existing_fields": ["customer_name", "satisfaction"]
    },
    headers={"Authorization": "Bearer your-token"}
)

suggestions = response.json()["suggestions"]
```

## Form Schema Structure

### Basic Field Structure
```json
{
  "name": "field_name",
  "type": "field_type",
  "label": "Field Label",
  "required": true,
  "validation": {
    "min_length": 5,
    "max_length": 100,
    "pattern": "^[A-Za-z]+$"
  },
  "appearance": {
    "placeholder": "Enter text here",
    "help_text": "Additional guidance"
  }
}
```

### Conditional Logic
```json
{
  "name": "follow_up_question",
  "type": "text",
  "label": "Please explain why",
  "relevant": "${satisfaction} = 'Dissatisfied' or ${satisfaction} = 'Very Dissatisfied'"
}
```

### Validation Rules
```json
{
  "validation": {
    "required": true,
    "min_value": 0,
    "max_value": 100,
    "regex": "^\\d{3}-\\d{3}-\\d{4}$",
    "custom": "function(value) { return value > 0; }"
  }
}
```

## Form Templates

### Available Templates
1. **Survey Template**: Basic survey with rating scales
2. **Registration Template**: User registration form
3. **Feedback Template**: Customer feedback collection
4. **Assessment Template**: Educational assessment form
5. **Inspection Template**: Quality inspection checklist
6. **Interview Template**: Structured interview form
7. **Application Template**: Job/program application form

### Creating Custom Templates
```python
template_data = {
    "name": "custom_survey",
    "title": "Custom Survey Template",
    "description": "Template for custom surveys",
    "category": "survey",
    "schema": {
        "fields": [
            # Template fields
        ]
    },
    "variables": [
        {
            "name": "survey_title",
            "type": "text",
            "label": "Survey Title",
            "default": "My Survey"
        }
    ]
}
```

## Integration

### With Data Collection Service
The Form Management service integrates seamlessly with the Data Collection service for submission handling:

```python
# Form validation before submission
form_schema = get_form_schema(form_id)
validate_submission(submission_data, form_schema)
```

### With AI Modules
Integration with AI modules for enhanced functionality:

```python
from ai_modules.form_recommendations import FormRecommender

recommender = FormRecommender()
suggestions = recommender.get_field_suggestions(form_context)
```

## Security

### Authentication
All endpoints require authentication via JWT tokens:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Authorization
Role-based access control:
- **Admin**: Full access to all forms
- **Manager**: Access to organization forms
- **User**: Access to own forms
- **Viewer**: Read-only access

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- Rate limiting

## Monitoring and Logging

### Health Check
```http
GET /health
```

### Metrics
- Form creation rate
- Validation error rate
- API response times
- Database connection status

### Logging
Comprehensive logging for:
- Form operations
- Validation errors
- Authentication attempts
- Performance metrics

## Development

### Running Locally
```bash
cd mcps/form_management
python src/main.py
```

### Testing
```bash
python -m pytest tests/unit/test_form_management.py
```

### Database Migrations
```bash
python scripts/run_migrations.sh form_management
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check DATABASE_URL configuration
   - Verify database server is running
   - Check network connectivity

2. **Form Validation Errors**
   - Verify form schema structure
   - Check field type compatibility
   - Validate JSON syntax

3. **AI Features Not Working**
   - Check OPENAI_API_KEY configuration
   - Verify AI_ENABLED setting
   - Check API quota limits

### Debug Mode
Enable debug mode for detailed error messages:
```env
FLASK_DEBUG=true
LOG_LEVEL=DEBUG
```

## Performance Optimization

### Database Optimization
- Use database indexes for frequently queried fields
- Implement connection pooling
- Use read replicas for analytics queries

### Caching
- Redis caching for frequently accessed forms
- CDN for static assets
- Browser caching for form schemas

### Scaling
- Horizontal scaling with load balancers
- Database sharding for large datasets
- Microservice architecture for independent scaling

## Contributing

Please refer to the main project [Contributing Guidelines](../../CONTRIBUTING.md) for information on how to contribute to this service.

## License

This service is part of the Enhanced ODK MCP System and is licensed under the MIT License.

