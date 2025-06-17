"""
Integration tests for the form to submission workflow.

This test verifies that forms created in the Form Management MCP can be used
to submit data in the Data Collection MCP, and that the data is correctly
stored and retrievable.
"""

import os
import json
import pytest
import requests
from flask import url_for
from datetime import datetime

def test_form_to_submission_workflow(app_form_management, app_data_collection, auth_token, test_xlsform):
    """Test the complete workflow from form creation to submission."""
    # Step 1: Create a form in the Form Management MCP
    form_id = None
    project_id = 1
    
    with app_form_management.app_context():
        # Create a test client
        client = app_form_management.test_client()
        
        # Create a form
        with open(test_xlsform, 'rb') as f:
            response = client.post(
                '/api/v1/forms',
                data={
                    'name': 'Integration Test Form',
                    'project_id': str(project_id),
                    'xlsform': (f, 'test_form.xlsx')
                },
                headers={'Authorization': f'Bearer {auth_token}'}
            )
        
        # Check that the form was created successfully
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        form_id = data['form_id']
    
    # Step 2: Submit data to the form in the Data Collection MCP
    submission_id = None
    
    with app_data_collection.app_context():
        # Create a test client
        client = app_data_collection.test_client()
        
        # Submit data
        response = client.post(
            '/api/v1/submissions',
            json={
                'form_id': form_id,
                'project_id': project_id,
                'data': {
                    'name': 'John Doe',
                    'gender': 'male',
                    'age': 30
                }
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Check that the submission was created successfully
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        submission_id = data['submission_id']
    
    # Step 3: Verify that the submission can be retrieved
    with app_data_collection.app_context():
        # Create a test client
        client = app_data_collection.test_client()
        
        # Get the submission
        response = client.get(
            f'/api/v1/submissions/{submission_id}',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Check that the submission was retrieved successfully
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['submission']['id'] == submission_id
        assert data['submission']['form_id'] == form_id
        assert data['submission']['project_id'] == project_id
        
        # Check that the submission data is correct
        submission_data = json.loads(data['submission']['data'])
        assert submission_data['name'] == 'John Doe'
        assert submission_data['gender'] == 'male'
        assert submission_data['age'] == 30

def test_form_validation_workflow(app_form_management, app_data_collection, auth_token, test_xlsform):
    """Test that form validation works correctly during submission."""
    # Step 1: Create a form with constraints in the Form Management MCP
    form_id = None
    project_id = 1
    
    # Create a form with constraints (age must be between 0 and 120)
    # In a real implementation, this would be part of the XLSForm
    # For this test, we'll simulate it by modifying the form after creation
    
    with app_form_management.app_context():
        # Create a test client
        client = app_form_management.test_client()
        
        # Create a form
        with open(test_xlsform, 'rb') as f:
            response = client.post(
                '/api/v1/forms',
                data={
                    'name': 'Validation Test Form',
                    'project_id': str(project_id),
                    'xlsform': (f, 'test_form.xlsx')
                },
                headers={'Authorization': f'Bearer {auth_token}'}
            )
        
        # Check that the form was created successfully
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        form_id = data['form_id']
        
        # Update the form with constraints
        from mcps.form_management.src.models.form import Form, db
        form = Form.query.get(form_id)
        
        # Add constraints to the JSON schema
        json_schema = json.loads(form.json_schema)
        json_schema['properties']['age'] = {
            'type': 'integer',
            'minimum': 0,
            'maximum': 120
        }
        form.json_schema = json.dumps(json_schema)
        db.session.commit()
    
    # Step 2: Submit valid data to the form
    with app_data_collection.app_context():
        # Create a test client
        client = app_data_collection.test_client()
        
        # Submit valid data
        response = client.post(
            '/api/v1/submissions',
            json={
                'form_id': form_id,
                'project_id': project_id,
                'data': {
                    'name': 'Jane Doe',
                    'gender': 'female',
                    'age': 25  # Valid age
                }
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Check that the submission was created successfully
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
    
    # Step 3: Submit invalid data to the form
    with app_data_collection.app_context():
        # Create a test client
        client = app_data_collection.test_client()
        
        # Submit invalid data (age out of range)
        response = client.post(
            '/api/v1/submissions',
            json={
                'form_id': form_id,
                'project_id': project_id,
                'data': {
                    'name': 'Invalid User',
                    'gender': 'male',
                    'age': 150  # Invalid age (> 120)
                }
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Check that the submission was rejected
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'validation' in data['message'].lower()

def test_form_update_submission_workflow(app_form_management, app_data_collection, auth_token, test_xlsform):
    """Test that form updates affect future submissions but not past ones."""
    # Step 1: Create a form in the Form Management MCP
    form_id = None
    project_id = 1
    
    with app_form_management.app_context():
        # Create a test client
        client = app_form_management.test_client()
        
        # Create a form
        with open(test_xlsform, 'rb') as f:
            response = client.post(
                '/api/v1/forms',
                data={
                    'name': 'Update Test Form',
                    'project_id': str(project_id),
                    'xlsform': (f, 'test_form.xlsx')
                },
                headers={'Authorization': f'Bearer {auth_token}'}
            )
        
        # Check that the form was created successfully
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        form_id = data['form_id']
    
    # Step 2: Submit data to the original form
    submission_id = None
    
    with app_data_collection.app_context():
        # Create a test client
        client = app_data_collection.test_client()
        
        # Submit data
        response = client.post(
            '/api/v1/submissions',
            json={
                'form_id': form_id,
                'project_id': project_id,
                'data': {
                    'name': 'Original User',
                    'gender': 'male',
                    'age': 40
                }
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Check that the submission was created successfully
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        submission_id = data['submission_id']
    
    # Step 3: Update the form
    with app_form_management.app_context():
        # Create a test client
        client = app_form_management.test_client()
        
        # Update the form (change version)
        response = client.put(
            f'/api/v1/forms/{form_id}',
            json={
                'name': 'Updated Test Form',
                'version': '2.0'
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Check that the form was updated successfully
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['form']['version'] == '2.0'
    
    # Step 4: Submit data to the updated form
    new_submission_id = None
    
    with app_data_collection.app_context():
        # Create a test client
        client = app_data_collection.test_client()
        
        # Submit data to the updated form
        response = client.post(
            '/api/v1/submissions',
            json={
                'form_id': form_id,
                'project_id': project_id,
                'data': {
                    'name': 'New User',
                    'gender': 'female',
                    'age': 35
                }
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Check that the submission was created successfully
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        new_submission_id = data['submission_id']
    
    # Step 5: Verify that both submissions can be retrieved
    with app_data_collection.app_context():
        # Create a test client
        client = app_data_collection.test_client()
        
        # Get the original submission
        response = client.get(
            f'/api/v1/submissions/{submission_id}',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Check that the original submission was retrieved successfully
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        submission_data = json.loads(data['submission']['data'])
        assert submission_data['name'] == 'Original User'
        
        # Get the new submission
        response = client.get(
            f'/api/v1/submissions/{new_submission_id}',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Check that the new submission was retrieved successfully
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        submission_data = json.loads(data['submission']['data'])
        assert submission_data['name'] == 'New User'

