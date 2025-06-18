"""
Cross-Project Analytics Service for ODK MCP System
Advanced analytics and comparison capabilities across multiple projects
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
import pandas as pd
import numpy as np
from scipy import stats
import plotly.graph_objects as go
import plotly.express as px
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

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
db_manager = get_database_manager('cross_project_analytics')
app.config['SQLALCHEMY_DATABASE_URI'] = db_manager.config.get_sqlalchemy_url()

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Cross-Project Analytics Models
class ProjectComparison(db.Model):
    __tablename__ = 'project_comparisons'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    project_ids = db.Column(db.JSON, nullable=False)
    comparison_type = db.Column(db.String(50), nullable=False)  # statistical, temporal, geographic, etc.
    
    # Configuration
    metrics = db.Column(db.JSON, nullable=False)
    filters = db.Column(db.JSON, default=lambda: {})
    grouping = db.Column(db.JSON, default=lambda: {})
    
    # Results
    results = db.Column(db.JSON)
    visualizations = db.Column(db.JSON)
    insights = db.Column(db.JSON)
    
    # Metadata
    created_by = db.Column(db.String(36), nullable=False)
    organization_id = db.Column(db.String(36), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'project_ids': self.project_ids,
            'comparison_type': self.comparison_type,
            'metrics': self.metrics,
            'filters': self.filters,
            'grouping': self.grouping,
            'results': self.results,
            'visualizations': self.visualizations,
            'insights': self.insights,
            'created_by': self.created_by,
            'organization_id': self.organization_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'status': self.status
        }

class AnalyticsReport(db.Model):
    __tablename__ = 'analytics_reports'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)  # summary, detailed, comparative, trend
    
    # Scope
    project_ids = db.Column(db.JSON, nullable=False)
    date_range = db.Column(db.JSON, nullable=False)
    
    # Content
    sections = db.Column(db.JSON, nullable=False)
    charts = db.Column(db.JSON, default=lambda: [])
    tables = db.Column(db.JSON, default=lambda: [])
    insights = db.Column(db.JSON, default=lambda: [])
    recommendations = db.Column(db.JSON, default=lambda: [])
    
    # Export formats
    pdf_path = db.Column(db.String(500))
    excel_path = db.Column(db.String(500))
    
    # Metadata
    created_by = db.Column(db.String(36), nullable=False)
    organization_id = db.Column(db.String(36), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Sharing
    is_public = db.Column(db.Boolean, default=False)
    shared_with = db.Column(db.JSON, default=lambda: [])
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'report_type': self.report_type,
            'project_ids': self.project_ids,
            'date_range': self.date_range,
            'sections': self.sections,
            'charts': self.charts,
            'tables': self.tables,
            'insights': self.insights,
            'recommendations': self.recommendations,
            'pdf_path': self.pdf_path,
            'excel_path': self.excel_path,
            'created_by': self.created_by,
            'organization_id': self.organization_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_public': self.is_public,
            'shared_with': self.shared_with
        }

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
            'service': 'cross_project_analytics',
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

# Cross-Project Comparison Endpoints
@app.route('/comparisons', methods=['GET'])
def list_comparisons():
    """List project comparisons"""
    
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        comparisons = ProjectComparison.query.filter_by(
            organization_id=g.organization_id
        ).order_by(ProjectComparison.updated_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'comparisons': [comp.to_dict() for comp in comparisons.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': comparisons.total,
                'pages': comparisons.pages
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing comparisons: {str(e)}")
        return jsonify({'error': 'Failed to list comparisons'}), 500

@app.route('/comparisons', methods=['POST'])
def create_comparison():
    """Create a new project comparison"""
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'project_ids', 'comparison_type', 'metrics']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create comparison
        comparison = ProjectComparison(
            name=data['name'],
            description=data.get('description', ''),
            project_ids=data['project_ids'],
            comparison_type=data['comparison_type'],
            metrics=data['metrics'],
            filters=data.get('filters', {}),
            grouping=data.get('grouping', {}),
            created_by=g.user_id,
            organization_id=g.organization_id
        )
        
        db.session.add(comparison)
        db.session.commit()
        
        # Trigger analysis
        perform_comparison_analysis(comparison.id)
        
        logger.info(f"Comparison created: {comparison.id}")
        
        return jsonify({
            'message': 'Comparison created successfully',
            'comparison': comparison.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating comparison: {str(e)}")
        return jsonify({'error': 'Failed to create comparison'}), 500

@app.route('/comparisons/<comparison_id>/analyze', methods=['POST'])
def analyze_comparison(comparison_id):
    """Perform analysis for a comparison"""
    
    try:
        comparison = ProjectComparison.query.filter_by(
            id=comparison_id,
            organization_id=g.organization_id
        ).first()
        
        if not comparison:
            return jsonify({'error': 'Comparison not found'}), 404
        
        # Update status
        comparison.status = 'processing'
        db.session.commit()
        
        # Perform analysis
        results = perform_comparison_analysis(comparison_id)
        
        return jsonify({
            'message': 'Analysis completed',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error analyzing comparison {comparison_id}: {str(e)}")
        return jsonify({'error': 'Failed to analyze comparison'}), 500

def perform_comparison_analysis(comparison_id):
    """Perform the actual comparison analysis"""
    
    try:
        comparison = ProjectComparison.query.get(comparison_id)
        if not comparison:
            return None
        
        # Get data for all projects
        project_data = {}
        for project_id in comparison.project_ids:
            data = get_project_data(project_id, comparison.filters)
            project_data[project_id] = data
        
        # Perform analysis based on comparison type
        if comparison.comparison_type == 'statistical':
            results = perform_statistical_comparison(project_data, comparison.metrics)
        elif comparison.comparison_type == 'temporal':
            results = perform_temporal_comparison(project_data, comparison.metrics)
        elif comparison.comparison_type == 'geographic':
            results = perform_geographic_comparison(project_data, comparison.metrics)
        elif comparison.comparison_type == 'demographic':
            results = perform_demographic_comparison(project_data, comparison.metrics)
        else:
            results = perform_general_comparison(project_data, comparison.metrics)
        
        # Generate visualizations
        visualizations = generate_comparison_visualizations(results, comparison.comparison_type)
        
        # Generate insights
        insights = generate_comparison_insights(results, comparison.comparison_type)
        
        # Update comparison with results
        comparison.results = results
        comparison.visualizations = visualizations
        comparison.insights = insights
        comparison.status = 'completed'
        comparison.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return results
        
    except Exception as e:
        logger.error(f"Error performing comparison analysis: {str(e)}")
        comparison.status = 'failed'
        db.session.commit()
        raise

def perform_statistical_comparison(project_data, metrics):
    """Perform statistical comparison between projects"""
    
    results = {
        'summary_statistics': {},
        'hypothesis_tests': {},
        'effect_sizes': {},
        'confidence_intervals': {}
    }
    
    for metric in metrics:
        metric_name = metric['name']
        metric_data = {}
        
        # Extract metric data from each project
        for project_id, data in project_data.items():
            if metric_name in data:
                metric_data[project_id] = data[metric_name]
        
        if len(metric_data) < 2:
            continue
        
        # Calculate summary statistics
        results['summary_statistics'][metric_name] = {}
        for project_id, values in metric_data.items():
            if values:
                results['summary_statistics'][metric_name][project_id] = {
                    'mean': np.mean(values),
                    'median': np.median(values),
                    'std': np.std(values),
                    'min': np.min(values),
                    'max': np.max(values),
                    'count': len(values)
                }
        
        # Perform hypothesis tests
        project_ids = list(metric_data.keys())
        if len(project_ids) == 2:
            # Two-sample t-test
            values1 = metric_data[project_ids[0]]
            values2 = metric_data[project_ids[1]]
            
            if len(values1) > 1 and len(values2) > 1:
                t_stat, p_value = stats.ttest_ind(values1, values2)
                results['hypothesis_tests'][metric_name] = {
                    'test': 'two_sample_t_test',
                    't_statistic': float(t_stat),
                    'p_value': float(p_value),
                    'significant': p_value < 0.05
                }
        
        elif len(project_ids) > 2:
            # ANOVA
            values_list = [metric_data[pid] for pid in project_ids if len(metric_data[pid]) > 1]
            if len(values_list) > 1:
                f_stat, p_value = stats.f_oneway(*values_list)
                results['hypothesis_tests'][metric_name] = {
                    'test': 'anova',
                    'f_statistic': float(f_stat),
                    'p_value': float(p_value),
                    'significant': p_value < 0.05
                }
    
    return results

def get_project_data(project_id, filters):
    """Get data for a specific project with filters applied"""
    
    # This would typically query the data collection service
    # For now, return mock data structure
    return {
        'submissions_count': np.random.randint(50, 500),
        'completion_rate': np.random.uniform(0.7, 0.95),
        'response_times': np.random.normal(120, 30, 100).tolist(),
        'satisfaction_scores': np.random.uniform(3, 5, 50).tolist(),
        'geographic_distribution': {
            'urban': np.random.randint(20, 80),
            'rural': np.random.randint(20, 80)
        }
    }

def generate_comparison_visualizations(results, comparison_type):
    """Generate visualizations for comparison results"""
    
    visualizations = []
    
    if 'summary_statistics' in results:
        # Create bar chart for means
        fig = go.Figure()
        
        for metric, projects in results['summary_statistics'].items():
            project_names = list(projects.keys())
            means = [projects[p]['mean'] for p in project_names]
            
            fig.add_trace(go.Bar(
                name=metric,
                x=project_names,
                y=means
            ))
        
        fig.update_layout(
            title='Mean Comparison Across Projects',
            xaxis_title='Projects',
            yaxis_title='Mean Values',
            barmode='group'
        )
        
        visualizations.append({
            'type': 'bar_chart',
            'title': 'Mean Comparison',
            'data': fig.to_json()
        })
    
    return visualizations

def generate_comparison_insights(results, comparison_type):
    """Generate insights from comparison results"""
    
    insights = []
    
    if 'hypothesis_tests' in results:
        for metric, test_result in results['hypothesis_tests'].items():
            if test_result['significant']:
                insights.append({
                    'type': 'significant_difference',
                    'metric': metric,
                    'message': f"Statistically significant difference found in {metric} (p={test_result['p_value']:.4f})",
                    'importance': 'high'
                })
            else:
                insights.append({
                    'type': 'no_difference',
                    'metric': metric,
                    'message': f"No statistically significant difference found in {metric}",
                    'importance': 'medium'
                })
    
    return insights

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
    port = int(os.getenv('CROSS_PROJECT_ANALYTICS_PORT', 5004))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Cross-Project Analytics service on port {port}")
    logger.info(f"Database type: {db_manager.config.database_type}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

