"""
Enhanced Form Management MCP Service with PostgreSQL Support
Dynamic configuration and production-ready features
"""

import os
import sys
import logging
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import uuid
import json

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared'))

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
db_manager = get_database_manager('form_management')
app.config['SQLALCHEMY_DATABASE_URI'] = db_manager.config.get_sqlalchemy_url()

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Enhanced Form Model
class Form(db.Model):
    __tablename__ = 'forms'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    version = db.Column(db.String(20), nullable=False, default='1.0.0')
    status = db.Column(db.String(20), nullable=False, default='draft')
    
    # Form structure and configuration
    form_definition = db.Column(db.JSON, nullable=False)
    settings = db.Column(db.JSON, default=lambda: {})
    
    # Metadata
    created_by = db.Column(db.String(36), nullable=False)
    project_id = db.Column(db.String(36), nullable=False)
    organization_id = db.Column(db.String(36), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    published_at = db.Column(db.DateTime)
    
    # Form analytics
    submission_count = db.Column(db.Integer, default=0)
    last_submission_at = db.Column(db.DateTime)
    
    # Access control
    is_public = db.Column(db.Boolean, default=False)
    allowed_users = db.Column(db.JSON, default=lambda: [])
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'version': self.version,
            'status': self.status,
            'form_definition': self.form_definition,
            'settings': self.settings,
            'created_by': self.created_by,
            'project_id': self.project_id,
            'organization_id': self.organization_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'submission_count': self.submission_count,
            'last_submission_at': self.last_submission_at.isoformat() if self.last_submission_at else None,
            'is_public': self.is_public,
            'allowed_users': self.allowed_users
        }

class FormVersion(db.Model):
    __tablename__ = 'form_versions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    form_id = db.Column(db.String(36), db.ForeignKey('forms.id'), nullable=False)
    version = db.Column(db.String(20), nullable=False)
    form_definition = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = db.Column(db.String(36), nullable=False)
    change_notes = db.Column(db.Text)

# Authentication middleware
@app.before_request
def authenticate_request():
    """Authenticate requests using API key or JWT token"""
    
    # Skip authentication for health check
    if request.endpoint == 'health':
        return
    
    # Get authentication token
    auth_header = request.headers.get('Authorization')
    api_key = request.headers.get('X-API-Key')
    
    if not auth_header and not api_key:
        return jsonify({'error': 'Authentication required'}), 401
    
    # For now, store user info in g for request context
    # In production, this would validate against user service
    g.user_id = request.headers.get('X-User-ID', 'anonymous')
    g.organization_id = request.headers.get('X-Organization-ID', 'default')

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'service': 'form_management',
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

# Form CRUD endpoints
@app.route('/forms', methods=['GET'])
def list_forms():
    """List forms with filtering and pagination"""
    
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        project_id = request.args.get('project_id')
        status = request.args.get('status')
        search = request.args.get('search')
        
        # Build query
        query = Form.query.filter_by(organization_id=g.organization_id)
        
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        if status:
            query = query.filter_by(status=status)
        
        if search:
            query = query.filter(
                db.or_(
                    Form.title.ilike(f'%{search}%'),
                    Form.description.ilike(f'%{search}%')
                )
            )
        
        # Execute query with pagination
        forms = query.order_by(Form.updated_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'forms': [form.to_dict() for form in forms.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': forms.total,
                'pages': forms.pages,
                'has_next': forms.has_next,
                'has_prev': forms.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing forms: {str(e)}")
        return jsonify({'error': 'Failed to list forms'}), 500

@app.route('/forms', methods=['POST'])
def create_form():
    """Create a new form"""
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'form_definition', 'project_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create new form
        form = Form(
            title=data['title'],
            description=data.get('description', ''),
            form_definition=data['form_definition'],
            settings=data.get('settings', {}),
            created_by=g.user_id,
            project_id=data['project_id'],
            organization_id=g.organization_id,
            is_public=data.get('is_public', False),
            allowed_users=data.get('allowed_users', [])
        )
        
        db.session.add(form)
        db.session.commit()
        
        # Create initial version
        version = FormVersion(
            form_id=form.id,
            version=form.version,
            form_definition=form.form_definition,
            created_by=g.user_id,
            change_notes='Initial version'
        )
        
        db.session.add(version)
        db.session.commit()
        
        logger.info(f"Form created: {form.id}")
        
        return jsonify({
            'message': 'Form created successfully',
            'form': form.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating form: {str(e)}")
        return jsonify({'error': 'Failed to create form'}), 500

@app.route('/forms/<form_id>', methods=['GET'])
def get_form(form_id):
    """Get a specific form"""
    
    try:
        form = Form.query.filter_by(
            id=form_id,
            organization_id=g.organization_id
        ).first()
        
        if not form:
            return jsonify({'error': 'Form not found'}), 404
        
        return jsonify({'form': form.to_dict()})
        
    except Exception as e:
        logger.error(f"Error getting form {form_id}: {str(e)}")
        return jsonify({'error': 'Failed to get form'}), 500

@app.route('/forms/<form_id>', methods=['PUT'])
def update_form(form_id):
    """Update a form"""
    
    try:
        form = Form.query.filter_by(
            id=form_id,
            organization_id=g.organization_id
        ).first()
        
        if not form:
            return jsonify({'error': 'Form not found'}), 404
        
        data = request.get_json()
        
        # Update form fields
        if 'title' in data:
            form.title = data['title']
        if 'description' in data:
            form.description = data['description']
        if 'form_definition' in data:
            form.form_definition = data['form_definition']
        if 'settings' in data:
            form.settings = data['settings']
        if 'status' in data:
            form.status = data['status']
            if data['status'] == 'published':
                form.published_at = datetime.now(timezone.utc)
        
        form.updated_at = datetime.now(timezone.utc)
        
        # Create new version if form definition changed
        if 'form_definition' in data:
            # Increment version
            version_parts = form.version.split('.')
            version_parts[-1] = str(int(version_parts[-1]) + 1)
            form.version = '.'.join(version_parts)
            
            # Create version record
            version = FormVersion(
                form_id=form.id,
                version=form.version,
                form_definition=form.form_definition,
                created_by=g.user_id,
                change_notes=data.get('change_notes', 'Form updated')
            )
            db.session.add(version)
        
        db.session.commit()
        
        logger.info(f"Form updated: {form.id}")
        
        return jsonify({
            'message': 'Form updated successfully',
            'form': form.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating form {form_id}: {str(e)}")
        return jsonify({'error': 'Failed to update form'}), 500

@app.route('/forms/<form_id>', methods=['DELETE'])
def delete_form(form_id):
    """Delete a form"""
    
    try:
        form = Form.query.filter_by(
            id=form_id,
            organization_id=g.organization_id
        ).first()
        
        if not form:
            return jsonify({'error': 'Form not found'}), 404
        
        # Delete form versions
        FormVersion.query.filter_by(form_id=form_id).delete()
        
        # Delete form
        db.session.delete(form)
        db.session.commit()
        
        logger.info(f"Form deleted: {form_id}")
        
        return jsonify({'message': 'Form deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting form {form_id}: {str(e)}")
        return jsonify({'error': 'Failed to delete form'}), 500

# Form analytics endpoints
@app.route('/forms/<form_id>/analytics', methods=['GET'])
def get_form_analytics(form_id):
    """Get form analytics"""
    
    try:
        form = Form.query.filter_by(
            id=form_id,
            organization_id=g.organization_id
        ).first()
        
        if not form:
            return jsonify({'error': 'Form not found'}), 404
        
        # In production, this would query the data collection service
        analytics = {
            'form_id': form_id,
            'submission_count': form.submission_count,
            'last_submission_at': form.last_submission_at.isoformat() if form.last_submission_at else None,
            'created_at': form.created_at.isoformat(),
            'status': form.status,
            'version': form.version
        }
        
        return jsonify({'analytics': analytics})
        
    except Exception as e:
        logger.error(f"Error getting form analytics {form_id}: {str(e)}")
        return jsonify({'error': 'Failed to get form analytics'}), 500

# Initialize database
@app.before_first_request
def create_tables():
    """Create database tables"""
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")

if __name__ == '__main__':
    port = int(os.getenv('FORM_MANAGEMENT_PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Form Management service on port {port}")
    logger.info(f"Database type: {db_manager.config.database_type}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

