"""
Unit tests for the Data Collection MCP.
"""

import os
import json
import pytest
from flask import url_for
from datetime import datetime

def test_submission_model(app_data_collection):
    """Test the Submission model."""
    from mcps.data_collection.src.models.submission import Submission, db
    
    with app_data_collection.app_context():
        # Create a submission
        submission = Submission(
            form_id=1,
            project_id=1,
            submitted_by='testuser',
            data='{"field1": "value1", "field2": "value2"}'
        )
        
        # Add the submission to the database
        db.session.add(submission)
        db.session.commit()
        
        # Query the submission
        queried_submission = Submission.query.filter_by(form_id=1).first()
        
        # Check that the submission was created correctly
        assert queried_submission is not None
        assert queried_submission.form_id == 1
        assert queried_submission.project_id == 1
        assert queried_submission.submitted_by == 'testuser'
        assert queried_submission.data == '{"field1": "value1", "field2": "value2"}'
        assert queried_submission.submitted_at is not None

def test_create_submission_api(client_data_collection, auth_token, test_form):
    """Test the create submission API endpoint."""
    # Create a test submission
    response = client_data_collection.post(
        '/api/v1/submissions',
        json={
            'form_id': test_form.id,
            'project_id': test_form.project_id,
            'data': {
                'field1': 'value1',
                'field2': 'value2'
            }
        },
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 201
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'submission_id' in data
    assert data['form_id'] == test_form.id
    assert data['project_id'] == test_form.project_id

def test_get_submission_api(client_data_collection, auth_token, test_submission):
    """Test the get submission API endpoint."""
    # Get the submission
    response = client_data_collection.get(
        f'/api/v1/submissions/{test_submission.id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['submission']['id'] == test_submission.id
    assert data['submission']['form_id'] == test_submission.form_id
    assert data['submission']['project_id'] == test_submission.project_id
    assert data['submission']['submitted_by'] == test_submission.submitted_by
    assert json.loads(data['submission']['data']) == json.loads(test_submission.data)

def test_list_submissions_api(client_data_collection, auth_token, test_submission):
    """Test the list submissions API endpoint."""
    # List submissions
    response = client_data_collection.get(
        '/api/v1/submissions',
        query_string={
            'project_id': test_submission.project_id,
            'form_id': test_submission.form_id
        },
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert len(data['submissions']) == 1
    assert data['submissions'][0]['id'] == test_submission.id
    assert data['submissions'][0]['form_id'] == test_submission.form_id
    assert data['submissions'][0]['project_id'] == test_submission.project_id
    assert data['submissions'][0]['submitted_by'] == test_submission.submitted_by

def test_update_submission_api(client_data_collection, auth_token, test_submission):
    """Test the update submission API endpoint."""
    # Update the submission
    response = client_data_collection.put(
        f'/api/v1/submissions/{test_submission.id}',
        json={
            'data': {
                'field1': 'updated_value1',
                'field2': 'updated_value2'
            }
        },
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['submission']['id'] == test_submission.id
    
    # Check that the submission was updated
    updated_data = json.loads(data['submission']['data'])
    assert updated_data['field1'] == 'updated_value1'
    assert updated_data['field2'] == 'updated_value2'

def test_delete_submission_api(client_data_collection, auth_token, test_submission):
    """Test the delete submission API endpoint."""
    # Delete the submission
    response = client_data_collection.delete(
        f'/api/v1/submissions/{test_submission.id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Check that the submission was deleted
    response = client_data_collection.get(
        f'/api/v1/submissions/{test_submission.id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the submission is not found
    assert response.status_code == 404

def test_bulk_submission_api(client_data_collection, auth_token, test_form):
    """Test the bulk submission API endpoint."""
    # Create multiple test submissions
    submissions = [
        {
            'form_id': test_form.id,
            'project_id': test_form.project_id,
            'data': {
                'field1': f'value{i}',
                'field2': f'value{i}'
            }
        }
        for i in range(3)
    ]
    
    # Submit the submissions
    response = client_data_collection.post(
        '/api/v1/submissions/bulk',
        json={
            'submissions': submissions
        },
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 201
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'submission_ids' in data
    assert len(data['submission_ids']) == 3

def test_sync_submissions_api(client_data_collection, auth_token, test_form):
    """Test the sync submissions API endpoint."""
    # Create a sync request
    response = client_data_collection.post(
        '/api/v1/submissions/sync',
        json={
            'project_id': test_form.project_id,
            'form_id': test_form.id,
            'last_sync': datetime.now().isoformat()
        },
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'submissions' in data
    assert 'last_sync' in data

