from flask import Blueprint, request, jsonify, current_app
from src.models.submission import db, Submission, SyncQueue
from src.utils.auth import auth_required, validate_submission_data, sanitize_submission_data
from datetime import datetime
import uuid
import logging
import requests

logger = logging.getLogger(__name__)

submissions_bp = Blueprint('submissions', __name__)

@submissions_bp.route('/projects/<project_id>/forms/<form_id>/submissions', methods=['POST'])
@auth_required(permissions=['data:submit'])
def submit_data(project_id, form_id):
    """Submit new data for a specific form within a project"""
    try:
        # Get submission data from request
        if not request.is_json:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'Content-Type must be application/json',
                'details': 'Submission data must be provided as JSON'
            }), 400
        
        submission_data = request.get_json()
        
        if not submission_data:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'Empty submission data',
                'details': 'Submission data cannot be empty'
            }), 400
        
        # Validate submission data
        is_valid, error_message = validate_submission_data(submission_data)
        if not is_valid:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'Invalid submission data',
                'details': error_message
            }), 400
        
        # Sanitize submission data
        clean_data = sanitize_submission_data(submission_data)
        
        # Extract metadata from submission
        instance_id = clean_data.get('meta', {}).get('instanceID') or str(uuid.uuid4())
        device_id = clean_data.get('meta', {}).get('deviceID')
        start_time = clean_data.get('meta', {}).get('timeStart')
        end_time = clean_data.get('meta', {}).get('timeEnd')
        
        # Parse datetime strings if provided
        start_datetime = None
        end_datetime = None
        
        if start_time:
            try:
                start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid start_time format: {start_time}")
        
        if end_time:
            try:
                end_datetime = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid end_time format: {end_time}")
        
        # Check if submission already exists
        existing_submission = Submission.query.filter_by(
            instance_id=instance_id,
            project_id=project_id,
            form_id=form_id
        ).first()
        
        if existing_submission:
            return jsonify({
                'code': 'CONFLICT',
                'message': 'Submission already exists',
                'details': f'Submission with instance ID {instance_id} already exists',
                'submission_id': existing_submission.submission_id
            }), 409
        
        # Create new submission
        new_submission = Submission(
            project_id=project_id,
            form_id=form_id,
            instance_id=instance_id,
            submitted_by=request.current_user,
            device_id=device_id,
            start_time=start_datetime,
            end_time=end_datetime
        )
        
        new_submission.set_submission_data(clean_data)
        
        # Handle attachments if present
        attachments = request.files.getlist('attachments')
        if attachments:
            attachment_metadata = []
            for attachment in attachments:
                if attachment.filename:
                    # In a real implementation, you would save the file to storage
                    # For now, we'll just store metadata
                    attachment_info = {
                        'filename': attachment.filename,
                        'content_type': attachment.content_type,
                        'size': len(attachment.read()),
                        'uploaded_at': datetime.utcnow().isoformat()
                    }
                    attachment_metadata.append(attachment_info)
            
            new_submission.set_attachments(attachment_metadata)
        
        db.session.add(new_submission)
        db.session.commit()
        
        # Trigger sync to Data Aggregation MCP (simulate)
        try:
            sync_success = _sync_to_aggregation_mcp(new_submission)
            if sync_success:
                new_submission.status = 'synced'
                new_submission.synced_at = datetime.utcnow()
                db.session.commit()
        except Exception as sync_error:
            logger.warning(f"Failed to sync submission {new_submission.submission_id}: {str(sync_error)}")
            # Add to sync queue for retry
            _add_to_sync_queue(new_submission, 'create')
        
        logger.info(f"Submission {new_submission.submission_id} created successfully by user {request.current_user}")
        
        return jsonify({
            'submission_id': new_submission.submission_id,
            'instance_id': new_submission.instance_id,
            'status': new_submission.status,
            'message': 'Submission created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating submission: {str(e)}")
        db.session.rollback()
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to create submission',
            'details': str(e)
        }), 500

@submissions_bp.route('/projects/<project_id>/forms/<form_id>/submissions/<submission_id>', methods=['GET'])
@auth_required(permissions=['data:read'])
def get_submission(project_id, form_id, submission_id):
    """Retrieve a specific submission"""
    try:
        submission = Submission.query.filter_by(
            submission_id=submission_id,
            project_id=project_id,
            form_id=form_id
        ).first()
        
        if not submission:
            return jsonify({
                'code': 'NOT_FOUND',
                'message': 'Submission not found',
                'details': f'Submission {submission_id} not found'
            }), 404
        
        return jsonify(submission.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error retrieving submission: {str(e)}")
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to retrieve submission',
            'details': str(e)
        }), 500

@submissions_bp.route('/projects/<project_id>/forms/<form_id>/submissions', methods=['GET'])
@auth_required(permissions=['data:read'])
def list_submissions(project_id, form_id):
    """List submissions for a specific form"""
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Build query
        query = Submission.query.filter_by(
            project_id=project_id,
            form_id=form_id
        )
        
        if status:
            query = query.filter_by(status=status)
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                query = query.filter(Submission.submitted_at >= start_dt)
            except ValueError:
                return jsonify({
                    'code': 'BAD_REQUEST',
                    'message': 'Invalid start_date format',
                    'details': 'Use ISO format: YYYY-MM-DDTHH:MM:SS'
                }), 400
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                query = query.filter(Submission.submitted_at <= end_dt)
            except ValueError:
                return jsonify({
                    'code': 'BAD_REQUEST',
                    'message': 'Invalid end_date format',
                    'details': 'Use ISO format: YYYY-MM-DDTHH:MM:SS'
                }), 400
        
        # Apply pagination
        submissions = query.order_by(Submission.submitted_at.desc()).paginate(
            page=page,
            per_page=limit,
            error_out=False
        )
        
        return jsonify({
            'submissions': [submission.to_dict() for submission in submissions.items],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': submissions.total,
                'pages': submissions.pages,
                'has_next': submissions.has_next,
                'has_prev': submissions.has_prev
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing submissions: {str(e)}")
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to retrieve submissions',
            'details': str(e)
        }), 500

@submissions_bp.route('/projects/<project_id>/forms/<form_id>/sync', methods=['POST'])
@auth_required(permissions=['data:submit'])
def sync_submissions(project_id, form_id):
    """Endpoint for bi-directional sync (pushing pending offline data)"""
    try:
        # Get sync data from request
        if not request.is_json:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'Content-Type must be application/json',
                'details': 'Sync data must be provided as JSON'
            }), 400
        
        sync_data = request.get_json()
        submissions_to_sync = sync_data.get('submissions', [])
        
        if not submissions_to_sync:
            return jsonify({
                'code': 'BAD_REQUEST',
                'message': 'No submissions to sync',
                'details': 'Provide submissions array in request body'
            }), 400
        
        sync_results = []
        
        for submission_data in submissions_to_sync:
            try:
                # Validate and sanitize submission data
                is_valid, error_message = validate_submission_data(submission_data)
                if not is_valid:
                    sync_results.append({
                        'instance_id': submission_data.get('meta', {}).get('instanceID', 'unknown'),
                        'status': 'error',
                        'message': error_message
                    })
                    continue
                
                clean_data = sanitize_submission_data(submission_data)
                instance_id = clean_data.get('meta', {}).get('instanceID') or str(uuid.uuid4())
                
                # Check if submission already exists
                existing_submission = Submission.query.filter_by(
                    instance_id=instance_id,
                    project_id=project_id,
                    form_id=form_id
                ).first()
                
                if existing_submission:
                    sync_results.append({
                        'instance_id': instance_id,
                        'submission_id': existing_submission.submission_id,
                        'status': 'exists',
                        'message': 'Submission already exists'
                    })
                    continue
                
                # Create new submission
                new_submission = Submission(
                    project_id=project_id,
                    form_id=form_id,
                    instance_id=instance_id,
                    submitted_by=request.current_user
                )
                
                new_submission.set_submission_data(clean_data)
                db.session.add(new_submission)
                db.session.flush()  # Get the ID without committing
                
                sync_results.append({
                    'instance_id': instance_id,
                    'submission_id': new_submission.submission_id,
                    'status': 'created',
                    'message': 'Submission created successfully'
                })
                
            except Exception as submission_error:
                logger.error(f"Error syncing individual submission: {str(submission_error)}")
                sync_results.append({
                    'instance_id': submission_data.get('meta', {}).get('instanceID', 'unknown'),
                    'status': 'error',
                    'message': str(submission_error)
                })
        
        db.session.commit()
        
        # Count results
        created_count = len([r for r in sync_results if r['status'] == 'created'])
        error_count = len([r for r in sync_results if r['status'] == 'error'])
        exists_count = len([r for r in sync_results if r['status'] == 'exists'])
        
        logger.info(f"Sync completed: {created_count} created, {exists_count} existing, {error_count} errors")
        
        return jsonify({
            'message': 'Sync completed',
            'summary': {
                'total': len(submissions_to_sync),
                'created': created_count,
                'existing': exists_count,
                'errors': error_count
            },
            'results': sync_results
        }), 200
        
    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")
        db.session.rollback()
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Sync failed',
            'details': str(e)
        }), 500

@submissions_bp.route('/sync/queue', methods=['GET'])
@auth_required(permissions=['data:read'])
def get_sync_queue():
    """Get pending sync queue items"""
    try:
        queue_items = SyncQueue.query.filter_by(status='pending').order_by(
            SyncQueue.priority.desc(),
            SyncQueue.created_at.asc()
        ).all()
        
        return jsonify({
            'queue_items': [item.to_dict() for item in queue_items],
            'count': len(queue_items)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving sync queue: {str(e)}")
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to retrieve sync queue',
            'details': str(e)
        }), 500

@submissions_bp.route('/sync/process', methods=['POST'])
@auth_required(permissions=['data:submit'])
def process_sync_queue():
    """Process pending sync queue items"""
    try:
        # Get pending items
        pending_items = SyncQueue.query.filter_by(status='pending').order_by(
            SyncQueue.priority.desc(),
            SyncQueue.created_at.asc()
        ).limit(10).all()  # Process up to 10 items at a time
        
        processed_count = 0
        failed_count = 0
        
        for item in pending_items:
            try:
                item.status = 'processing'
                item.last_attempt = datetime.utcnow()
                db.session.commit()
                
                # Simulate sync operation
                success = _process_sync_item(item)
                
                if success:
                    item.status = 'completed'
                    processed_count += 1
                else:
                    item.retry_count += 1
                    if item.retry_count >= item.max_retries:
                        item.status = 'failed'
                        failed_count += 1
                    else:
                        item.status = 'pending'
                
                db.session.commit()
                
            except Exception as item_error:
                logger.error(f"Error processing sync item {item.id}: {str(item_error)}")
                item.status = 'pending'
                item.retry_count += 1
                item.error_message = str(item_error)
                
                if item.retry_count >= item.max_retries:
                    item.status = 'failed'
                    failed_count += 1
                
                db.session.commit()
        
        return jsonify({
            'message': 'Sync queue processed',
            'processed': processed_count,
            'failed': failed_count,
            'total_items': len(pending_items)
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing sync queue: {str(e)}")
        return jsonify({
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to process sync queue',
            'details': str(e)
        }), 500

def _sync_to_aggregation_mcp(submission):
    """Sync submission to Data Aggregation MCP"""
    try:
        # In a real implementation, this would make an HTTP request to the DAA_MCP
        # For now, we'll simulate success
        logger.info(f"Syncing submission {submission.submission_id} to Data Aggregation MCP")
        return True
    except Exception as e:
        logger.error(f"Failed to sync to aggregation MCP: {str(e)}")
        return False

def _add_to_sync_queue(submission, operation):
    """Add submission to sync queue for retry"""
    try:
        queue_item = SyncQueue(
            submission_id=submission.submission_id,
            project_id=submission.project_id,
            form_id=submission.form_id,
            operation=operation
        )
        
        queue_item.set_payload({
            'submission_data': submission.get_submission_data(),
            'attachments': submission.get_attachments(),
            'metadata': {
                'instance_id': submission.instance_id,
                'submitted_by': submission.submitted_by,
                'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None
            }
        })
        
        db.session.add(queue_item)
        db.session.commit()
        
        logger.info(f"Added submission {submission.submission_id} to sync queue")
        
    except Exception as e:
        logger.error(f"Failed to add to sync queue: {str(e)}")

def _process_sync_item(sync_item):
    """Process a single sync queue item"""
    try:
        # In a real implementation, this would make the appropriate API call
        # based on the operation type (create, update, delete)
        logger.info(f"Processing sync item {sync_item.id} - operation: {sync_item.operation}")
        
        # Simulate processing
        return True
        
    except Exception as e:
        logger.error(f"Failed to process sync item {sync_item.id}: {str(e)}")
        return False

