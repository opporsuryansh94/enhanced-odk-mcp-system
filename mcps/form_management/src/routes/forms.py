from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from src.models.form import db, Form
from src.utils.auth import auth_required
from src.utils.xlsform import XLSFormProcessor, parse_xlsform_file
import uuid
import logging
import io

logger = logging.getLogger(__name__)

forms_bp = Blueprint('forms', __name__)

# Initialize XLSForm processor
xlsform_processor = XLSFormProcessor()

@forms_bp.route('/projects/<project_id>/forms', methods=['POST'])
@auth_required(permissions=['form:create', 'project:manage'])
def upload_form(project_id):
    """Upload a new XLSForm for a given project"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'No file provided',
                'details': 'XLSForm file is required'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'No file selected',
                'details': 'Please select an XLSForm file'
            }), 400
        
        # Get form metadata from request
        form_name = request.form.get('name') or file.filename.rsplit('.', 1)[0]
        form_description = request.form.get('description', '')
        
        # Validate file type
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'Invalid file type',
                'details': 'Only Excel files (.xlsx, .xls) are supported'
            }), 400
        
        # Parse XLSForm file
        file_content = file.read()
        xlsform_data = parse_xlsform_file(file_content, file.filename)
        
        # Process XLSForm and generate XForm
        processing_result = xlsform_processor.process_xlsform(xlsform_data)
        
        if not processing_result['success']:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'Invalid XLSForm',
                'details': processing_result['error']
            }), 400
        
        # Generate unique form ID
        form_id = processing_result['form_metadata']['form_id']
        
        # Check if form already exists in this project
        existing_form = Form.query.filter_by(
            form_id=form_id, 
            project_id=project_id
        ).first()
        
        if existing_form:
            return jsonify({
                'code': 'CONFLICT',
                'message': 'Form already exists',
                'details': f'Form with ID {form_id} already exists in this project'
            }), 409
        
        # Create new form record
        new_form = Form(
            form_id=form_id,
            project_id=project_id,
            name=form_name,
            description=form_description,
            version=processing_result['form_metadata']['version'],
            xlsform_content=processing_result['xlsform_data'],
            xform_content=processing_result['xform_xml'],
            created_by=request.current_user
        )
        
        new_form.set_xlsform_json(processing_result['xlsform_data'])
        
        db.session.add(new_form)
        db.session.commit()
        
        logger.info(f"Form {form_id} uploaded successfully by user {request.current_user}")
        
        return jsonify({
            'form_id': form_id,
            'status': 'success',
            'message': 'Form uploaded successfully',
            'xform_url': f'/v1/projects/{project_id}/forms/{form_id}/xform',
            'metadata': processing_result['form_metadata']
        }), 201
        
    except Exception as e:
        logger.error(f"Error uploading form: {str(e)}")
        db.session.rollback()
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to upload form',
            'details': str(e)
        }), 500

@forms_bp.route('/projects/<project_id>/forms', methods=['GET'])
@auth_required(permissions=['form:read'])
def list_forms(project_id):
    """List all forms for a given project"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        status = request.args.get('status')
        
        # Build query
        query = Form.query.filter_by(project_id=project_id)
        
        if status:
            query = query.filter_by(status=status)
        
        # Apply pagination
        forms = query.paginate(
            page=page, 
            per_page=limit, 
            error_out=False
        )
        
        return jsonify({
            'forms': [form.to_dict() for form in forms.items],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': forms.total,
                'pages': forms.pages,
                'has_next': forms.has_next,
                'has_prev': forms.has_prev
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing forms: {str(e)}")
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to retrieve forms',
            'details': str(e)
        }), 500

@forms_bp.route('/projects/<project_id>/forms/<form_id>', methods=['GET'])
@auth_required(permissions=['form:read'])
def get_form(project_id, form_id):
    """Retrieve metadata for a specific form"""
    try:
        form = Form.query.filter_by(
            form_id=form_id, 
            project_id=project_id
        ).first()
        
        if not form:
            return jsonify({
                'code': 'NOT_FOUND',
                'message': 'Form not found',
                'details': f'Form {form_id} not found in project {project_id}'
            }), 404
        
        form_data = form.to_dict()
        form_data['xlsform_data'] = form.get_xlsform_json()
        
        return jsonify(form_data), 200
        
    except Exception as e:
        logger.error(f"Error retrieving form: {str(e)}")
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to retrieve form',
            'details': str(e)
        }), 500

@forms_bp.route('/projects/<project_id>/forms/<form_id>/xform', methods=['GET'])
@auth_required(permissions=['form:read'])
def get_xform(project_id, form_id):
    """Retrieve the compiled XForm XML for a specific form"""
    try:
        form = Form.query.filter_by(
            form_id=form_id, 
            project_id=project_id
        ).first()
        
        if not form:
            return jsonify({
                'code': 'NOT_FOUND',
                'message': 'Form not found',
                'details': f'Form {form_id} not found in project {project_id}'
            }), 404
        
        if not form.xform_content:
            return jsonify({
                'code': 'NOT_FOUND',
                'message': 'XForm not available',
                'details': 'XForm XML has not been generated for this form'
            }), 404
        
        return current_app.response_class(
            form.xform_content,
            mimetype='application/xml',
            headers={'Content-Disposition': f'attachment; filename="{form_id}.xml"'}
        )
        
    except Exception as e:
        logger.error(f"Error retrieving XForm: {str(e)}")
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to retrieve XForm',
            'details': str(e)
        }), 500

@forms_bp.route('/projects/<project_id>/forms/<form_id>', methods=['PUT'])
@auth_required(permissions=['form:update', 'project:manage'])
def update_form(project_id, form_id):
    """Update an existing form"""
    try:
        form = Form.query.filter_by(
            form_id=form_id, 
            project_id=project_id
        ).first()
        
        if not form:
            return jsonify({
                'code': 'NOT_FOUND',
                'message': 'Form not found',
                'details': f'Form {form_id} not found in project {project_id}'
            }), 404
        
        # Check if new file is provided
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                # Validate file type
                if not file.filename.lower().endswith(('.xlsx', '.xls')):
                    return jsonify({
                        'code': 'BAD_REQUEST',
                        'message': 'Invalid file type',
                        'details': 'Only Excel files (.xlsx, .xls) are supported'
                    }), 400
                
                # Parse and process new XLSForm
                file_content = file.read()
                xlsform_data = parse_xlsform_file(file_content, file.filename)
                processing_result = xlsform_processor.process_xlsform(xlsform_data)
                
                if not processing_result['success']:
                    return jsonify({
                        'code': 'BAD_REQUEST',
                        'message': 'Invalid XLSForm',
                        'details': processing_result['error']
                    }), 400
                
                # Update form content
                form.set_xlsform_json(processing_result['xlsform_data'])
                form.xform_content = processing_result['xform_xml']
                form.version = processing_result['form_metadata']['version']
        
        # Update metadata if provided
        if 'name' in request.form:
            form.name = request.form['name']
        if 'description' in request.form:
            form.description = request.form['description']
        if 'status' in request.form:
            form.status = request.form['status']
        
        db.session.commit()
        
        logger.info(f"Form {form_id} updated successfully by user {request.current_user}")
        
        return jsonify({
            'message': 'Form updated successfully',
            'form': form.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating form: {str(e)}")
        db.session.rollback()
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to update form',
            'details': str(e)
        }), 500

@forms_bp.route('/projects/<project_id>/forms/<form_id>', methods=['DELETE'])
@auth_required(permissions=['form:delete', 'project:manage'])
def delete_form(project_id, form_id):
    """Delete a form"""
    try:
        form = Form.query.filter_by(
            form_id=form_id, 
            project_id=project_id
        ).first()
        
        if not form:
            return jsonify({
                'code': 'NOT_FOUND',
                'message': 'Form not found',
                'details': f'Form {form_id} not found in project {project_id}'
            }), 404
        
        db.session.delete(form)
        db.session.commit()
        
        logger.info(f"Form {form_id} deleted successfully by user {request.current_user}")
        
        return jsonify({
            'message': 'Form deleted successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting form: {str(e)}")
        db.session.rollback()
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to delete form',
            'details': str(e)
        }), 500

