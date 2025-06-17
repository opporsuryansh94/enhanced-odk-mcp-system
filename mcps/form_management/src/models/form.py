from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Form(db.Model):
    """Form model for storing ODK form definitions"""
    __tablename__ = 'forms'
    
    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    version = db.Column(db.String(50), default='1.0')
    xlsform_content = db.Column(db.Text)  # Store XLSForm as JSON
    xform_content = db.Column(db.Text)    # Store compiled XForm XML
    status = db.Column(db.String(50), default='active')  # active, inactive, draft
    created_by = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert form to dictionary"""
        return {
            'id': self.id,
            'form_id': self.form_id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_xlsform_json(self):
        """Get XLSForm content as JSON"""
        if self.xlsform_content:
            try:
                return json.loads(self.xlsform_content)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_xlsform_json(self, xlsform_data):
        """Set XLSForm content from JSON"""
        if xlsform_data:
            self.xlsform_content = json.dumps(xlsform_data)
        else:
            self.xlsform_content = None

