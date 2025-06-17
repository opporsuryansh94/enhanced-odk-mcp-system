from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import uuid

db = SQLAlchemy()

class Submission(db.Model):
    """Submission model for storing ODK form submissions"""
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    form_id = db.Column(db.String(255), nullable=False, index=True)
    instance_id = db.Column(db.String(255), unique=True, nullable=False)
    submission_data = db.Column(db.Text, nullable=False)  # JSON string of form data
    attachments = db.Column(db.Text)  # JSON string of attachment metadata
    status = db.Column(db.String(50), default='submitted')  # submitted, synced, error
    submitted_by = db.Column(db.String(255), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    synced_at = db.Column(db.DateTime)
    device_id = db.Column(db.String(255))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.submission_id:
            self.submission_id = str(uuid.uuid4())
        if not self.instance_id:
            self.instance_id = str(uuid.uuid4())
    
    def to_dict(self):
        """Convert submission to dictionary"""
        return {
            'id': self.id,
            'submission_id': self.submission_id,
            'project_id': self.project_id,
            'form_id': self.form_id,
            'instance_id': self.instance_id,
            'status': self.status,
            'submitted_by': self.submitted_by,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None,
            'device_id': self.device_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'data': self.get_submission_data(),
            'attachments': self.get_attachments()
        }
    
    def get_submission_data(self):
        """Get submission data as JSON"""
        if self.submission_data:
            try:
                return json.loads(self.submission_data)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_submission_data(self, data):
        """Set submission data from dictionary"""
        if data:
            self.submission_data = json.dumps(data)
        else:
            self.submission_data = None
    
    def get_attachments(self):
        """Get attachments metadata as JSON"""
        if self.attachments:
            try:
                return json.loads(self.attachments)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_attachments(self, attachments_list):
        """Set attachments metadata from list"""
        if attachments_list:
            self.attachments = json.dumps(attachments_list)
        else:
            self.attachments = None

class SyncQueue(db.Model):
    """Queue for managing offline submissions that need to be synced"""
    __tablename__ = 'sync_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.String(255), nullable=False, index=True)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    form_id = db.Column(db.String(255), nullable=False, index=True)
    operation = db.Column(db.String(50), nullable=False)  # create, update, delete
    payload = db.Column(db.Text, nullable=False)  # JSON payload for the operation
    priority = db.Column(db.Integer, default=1)  # Higher number = higher priority
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_attempt = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    def to_dict(self):
        """Convert sync queue item to dictionary"""
        return {
            'id': self.id,
            'submission_id': self.submission_id,
            'project_id': self.project_id,
            'form_id': self.form_id,
            'operation': self.operation,
            'priority': self.priority,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_attempt': self.last_attempt.isoformat() if self.last_attempt else None,
            'error_message': self.error_message,
            'payload': self.get_payload()
        }
    
    def get_payload(self):
        """Get payload as JSON"""
        if self.payload:
            try:
                return json.loads(self.payload)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_payload(self, data):
        """Set payload from dictionary"""
        if data:
            self.payload = json.dumps(data)
        else:
            self.payload = None

