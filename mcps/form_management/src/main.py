import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from src.models.form import db, Form
from src.routes.forms import forms_bp
from src.utils.auth import auth_required
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'form-management-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')

# Enable CORS for all routes
CORS(app, origins="*")

# Initialize JWT
jwt = JWTManager(app)

# Register blueprints
app.register_blueprint(forms_bp, url_prefix='/v1')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Form Definition & Management MCP',
        'version': '1.0.0'
    }), 200

@app.errorhandler(400)
def bad_request(error):
    logger.warning(f"Bad request: {error}")
    return jsonify({
        'code': 'BAD_REQUEST',
        'message': 'Invalid request format or parameters',
        'details': str(error)
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    logger.warning(f"Unauthorized access: {error}")
    return jsonify({
        'code': 'UNAUTHORIZED',
        'message': 'Authentication required or invalid token',
        'details': str(error)
    }), 401

@app.errorhandler(403)
def forbidden(error):
    logger.warning(f"Forbidden access: {error}")
    return jsonify({
        'code': 'FORBIDDEN',
        'message': 'Insufficient permissions for this action',
        'details': str(error)
    }), 403

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"Resource not found: {error}")
    return jsonify({
        'code': 'NOT_FOUND',
        'message': 'Requested resource not found',
        'details': str(error)
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'code': 'INTERNAL_ERROR',
        'message': 'An unexpected error occurred',
        'details': 'Please contact system administrator'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

