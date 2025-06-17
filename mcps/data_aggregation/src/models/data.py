from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import uuid

# Import db from user module to maintain consistency
from src.models.user import db

class AggregatedData(db.Model):
    """Model for storing aggregated submission data"""
    __tablename__ = 'aggregated_data'
    
    id = db.Column(db.Integer, primary_key=True)
    data_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    form_id = db.Column(db.String(255), nullable=False, index=True)
    submission_id = db.Column(db.String(255), nullable=False, index=True)
    instance_id = db.Column(db.String(255), nullable=False, index=True)
    
    # Data fields
    submission_data = db.Column(db.Text, nullable=False)  # JSON string of form data
    metadata = db.Column(db.Text)  # JSON string of submission metadata
    
    # Tracking fields
    submitted_by = db.Column(db.String(255), nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False)
    aggregated_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Data quality and processing fields
    is_processed = db.Column(db.Boolean, default=False)
    processing_status = db.Column(db.String(50), default='raw')  # raw, cleaned, processed, error
    quality_score = db.Column(db.Float)  # Data quality score (0-1)
    validation_errors = db.Column(db.Text)  # JSON string of validation errors
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.data_id:
            self.data_id = str(uuid.uuid4())
    
    def to_dict(self, include_data=True):
        """Convert aggregated data to dictionary"""
        result = {
            'id': self.id,
            'data_id': self.data_id,
            'project_id': self.project_id,
            'form_id': self.form_id,
            'submission_id': self.submission_id,
            'instance_id': self.instance_id,
            'submitted_by': self.submitted_by,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'aggregated_at': self.aggregated_at.isoformat() if self.aggregated_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_processed': self.is_processed,
            'processing_status': self.processing_status,
            'quality_score': self.quality_score,
            'validation_errors': self.get_validation_errors()
        }
        
        if include_data:
            result['data'] = self.get_submission_data()
            result['metadata'] = self.get_metadata()
        
        return result
    
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
    
    def get_metadata(self):
        """Get metadata as JSON"""
        if self.metadata:
            try:
                return json.loads(self.metadata)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_metadata(self, metadata_dict):
        """Set metadata from dictionary"""
        if metadata_dict:
            self.metadata = json.dumps(metadata_dict)
        else:
            self.metadata = None
    
    def get_validation_errors(self):
        """Get validation errors as JSON"""
        if self.validation_errors:
            try:
                return json.loads(self.validation_errors)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_validation_errors(self, errors_list):
        """Set validation errors from list"""
        if errors_list:
            self.validation_errors = json.dumps(errors_list)
        else:
            self.validation_errors = None

class DataAnalysisResult(db.Model):
    """Model for storing analysis results"""
    __tablename__ = 'analysis_results'
    
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    project_id = db.Column(db.String(255), nullable=False, index=True)
    analysis_type = db.Column(db.String(100), nullable=False)  # descriptive, inferential, exploration
    analysis_name = db.Column(db.String(255), nullable=False)
    
    # Analysis configuration and results
    parameters = db.Column(db.Text)  # JSON string of analysis parameters
    results = db.Column(db.Text, nullable=False)  # JSON string of analysis results
    visualizations = db.Column(db.Text)  # JSON string of visualization data
    
    # Metadata
    created_by = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    execution_time = db.Column(db.Float)  # Execution time in seconds
    data_count = db.Column(db.Integer)  # Number of data points analyzed
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.result_id:
            self.result_id = str(uuid.uuid4())
    
    def to_dict(self, include_results=True):
        """Convert analysis result to dictionary"""
        result = {
            'id': self.id,
            'result_id': self.result_id,
            'project_id': self.project_id,
            'analysis_type': self.analysis_type,
            'analysis_name': self.analysis_name,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'execution_time': self.execution_time,
            'data_count': self.data_count,
            'parameters': self.get_parameters()
        }
        
        if include_results:
            result['results'] = self.get_results()
            result['visualizations'] = self.get_visualizations()
        
        return result
    
    def get_parameters(self):
        """Get parameters as JSON"""
        if self.parameters:
            try:
                return json.loads(self.parameters)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_parameters(self, params_dict):
        """Set parameters from dictionary"""
        if params_dict:
            self.parameters = json.dumps(params_dict)
        else:
            self.parameters = None
    
    def get_results(self):
        """Get results as JSON"""
        if self.results:
            try:
                return json.loads(self.results)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_results(self, results_dict):
        """Set results from dictionary"""
        if results_dict:
            self.results = json.dumps(results_dict)
        else:
            self.results = None
    
    def get_visualizations(self):
        """Get visualizations as JSON"""
        if self.visualizations:
            try:
                return json.loads(self.visualizations)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_visualizations(self, viz_list):
        """Set visualizations from list"""
        if viz_list:
            self.visualizations = json.dumps(viz_list)
        else:
            self.visualizations = None

