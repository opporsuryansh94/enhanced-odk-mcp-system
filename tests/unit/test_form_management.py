"""
Unit tests for the Form Management MCP.
"""

import os
import json
import pytest
from flask import url_for

def test_form_model(app_form_management):
    """Test the Form model."""
    from mcps.form_management.src.models.form import Form, db
    
    with app_form_management.app_context():
        # Create a form
        form = Form(
            name='Test Form',
            project_id=1,
            version='1.0',
            created_by='testuser',
            xml_content='<form>Test Form</form>',
            json_schema='{"type": "object"}'
        )
        
        # Add the form to the database
        db.session.add(form)
        db.session.commit()
        
        # Query the form
        queried_form = Form.query.filter_by(name='Test Form').first()
        
        # Check that the form was created correctly
        assert queried_form is not None
        assert queried_form.name == 'Test Form'
        assert queried_form.project_id == 1
        assert queried_form.version == '1.0'
        assert queried_form.created_by == 'testuser'
        assert queried_form.xml_content == '<form>Test Form</form>'
        assert queried_form.json_schema == '{"type": "object"}'

def test_xlsform_conversion(app_form_management, test_xlsform):
    """Test XLSForm to XForm conversion."""
    from mcps.form_management.src.utils.xlsform import convert_xlsform_to_xform
    
    with app_form_management.app_context():
        # Convert the XLSForm to XForm
        result = convert_xlsform_to_xform(test_xlsform)
        
        # Check that the conversion was successful
        assert result['success'] is True
        assert 'xform' in result
        assert 'json_schema' in result
        
        # Check that the XForm contains the expected elements
        assert '<h:title>Test Form</h:title>' in result['xform']
        assert '<name/>' in result['xform']
        assert '<gender/>' in result['xform']
        assert '<age/>' in result['xform']
        
        # Check that the JSON schema contains the expected properties
        json_schema = json.loads(result['json_schema'])
        assert 'properties' in json_schema
        assert 'name' in json_schema['properties']
        assert 'gender' in json_schema['properties']
        assert 'age' in json_schema['properties']

def test_create_form_api(client_form_management, auth_token, test_xlsform):
    """Test the create form API endpoint."""
    # Create a test form
    with open(test_xlsform, 'rb') as f:
        response = client_form_management.post(
            '/api/v1/forms',
            data={
                'name': 'Test Form',
                'project_id': '1',
                'xlsform': (f, 'test_form.xlsx')
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
    
    # Check that the response is successful
    assert response.status_code == 201
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'form_id' in data
    assert data['name'] == 'Test Form'
    assert data['project_id'] == 1

def test_get_form_api(client_form_management, auth_token, test_form):
    """Test the get form API endpoint."""
    # Get the form
    response = client_form_management.get(
        f'/api/v1/forms/{test_form.id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['form']['id'] == test_form.id
    assert data['form']['name'] == test_form.name
    assert data['form']['project_id'] == test_form.project_id
    assert data['form']['version'] == test_form.version
    assert data['form']['created_by'] == test_form.created_by

def test_list_forms_api(client_form_management, auth_token, test_form):
    """Test the list forms API endpoint."""
    # List forms
    response = client_form_management.get(
        '/api/v1/forms',
        query_string={'project_id': test_form.project_id},
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert len(data['forms']) == 1
    assert data['forms'][0]['id'] == test_form.id
    assert data['forms'][0]['name'] == test_form.name
    assert data['forms'][0]['project_id'] == test_form.project_id

def test_update_form_api(client_form_management, auth_token, test_form):
    """Test the update form API endpoint."""
    # Update the form
    response = client_form_management.put(
        f'/api/v1/forms/{test_form.id}',
        json={
            'name': 'Updated Test Form',
            'version': '1.1'
        },
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['form']['id'] == test_form.id
    assert data['form']['name'] == 'Updated Test Form'
    assert data['form']['version'] == '1.1'

def test_delete_form_api(client_form_management, auth_token, test_form):
    """Test the delete form API endpoint."""
    # Delete the form
    response = client_form_management.delete(
        f'/api/v1/forms/{test_form.id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Check that the form was deleted
    response = client_form_management.get(
        f'/api/v1/forms/{test_form.id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the form is not found
    assert response.status_code == 404

