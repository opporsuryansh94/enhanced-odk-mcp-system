"""
Unit tests for the Data Aggregation MCP.
"""

import os
import json
import pytest
from flask import url_for
from datetime import datetime

def test_user_model(app_data_aggregation):
    """Test the User model."""
    from mcps.data_aggregation.src.models.user import User, Role, db
    
    with app_data_aggregation.app_context():
        # Create a user
        user = User(
            username='testuser',
            email='test@example.com',
            role=Role.ADMIN
        )
        user.set_password('testpassword')
        
        # Add the user to the database
        db.session.add(user)
        db.session.commit()
        
        # Query the user
        queried_user = User.query.filter_by(username='testuser').first()
        
        # Check that the user was created correctly
        assert queried_user is not None
        assert queried_user.username == 'testuser'
        assert queried_user.email == 'test@example.com'
        assert queried_user.role == Role.ADMIN
        assert queried_user.check_password('testpassword') is True
        assert queried_user.check_password('wrongpassword') is False

def test_project_model(app_data_aggregation):
    """Test the Project model."""
    from mcps.data_aggregation.src.models.user import User, Role, Project, UserProject, db
    
    with app_data_aggregation.app_context():
        # Create a user
        user = User(
            username='testuser',
            email='test@example.com',
            role=Role.ADMIN
        )
        user.set_password('testpassword')
        db.session.add(user)
        db.session.commit()
        
        # Create a project
        project = Project(
            name='Test Project',
            description='A test project',
            created_by=user.id
        )
        db.session.add(project)
        db.session.commit()
        
        # Associate the user with the project
        user_project = UserProject(
            user_id=user.id,
            project_id=project.id,
            role=Role.ADMIN
        )
        db.session.add(user_project)
        db.session.commit()
        
        # Query the project
        queried_project = Project.query.filter_by(name='Test Project').first()
        
        # Check that the project was created correctly
        assert queried_project is not None
        assert queried_project.name == 'Test Project'
        assert queried_project.description == 'A test project'
        assert queried_project.created_by == user.id
        
        # Check that the user is associated with the project
        user_projects = UserProject.query.filter_by(user_id=user.id, project_id=project.id).all()
        assert len(user_projects) == 1
        assert user_projects[0].role == Role.ADMIN

def test_register_api(client_data_aggregation):
    """Test the register API endpoint."""
    # Register a new user
    response = client_data_aggregation.post(
        '/api/v1/auth/register',
        json={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpassword'
        }
    )
    
    # Check that the response is successful
    assert response.status_code == 201
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'user_id' in data
    assert data['username'] == 'newuser'
    assert data['email'] == 'newuser@example.com'
    assert 'token' in data

def test_login_api(client_data_aggregation):
    """Test the login API endpoint."""
    # Create a user
    from mcps.data_aggregation.src.models.user import User, Role, db
    
    with client_data_aggregation.application.app_context():
        user = User(
            username='loginuser',
            email='loginuser@example.com',
            role=Role.USER
        )
        user.set_password('loginpassword')
        db.session.add(user)
        db.session.commit()
    
    # Login with the user
    response = client_data_aggregation.post(
        '/api/v1/auth/login',
        json={
            'username': 'loginuser',
            'password': 'loginpassword'
        }
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['user']['username'] == 'loginuser'
    assert data['user']['email'] == 'loginuser@example.com'
    assert 'token' in data

def test_create_project_api(client_data_aggregation, auth_token):
    """Test the create project API endpoint."""
    # Create a project
    response = client_data_aggregation.post(
        '/api/v1/projects',
        json={
            'name': 'API Test Project',
            'description': 'A project created through the API'
        },
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 201
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'project_id' in data
    assert data['name'] == 'API Test Project'
    assert data['description'] == 'A project created through the API'

def test_get_project_api(client_data_aggregation, auth_token, test_project):
    """Test the get project API endpoint."""
    # Get the project
    response = client_data_aggregation.get(
        f'/api/v1/projects/{test_project.id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['project']['id'] == test_project.id
    assert data['project']['name'] == test_project.name
    assert data['project']['description'] == test_project.description

def test_list_projects_api(client_data_aggregation, auth_token, test_project):
    """Test the list projects API endpoint."""
    # List projects
    response = client_data_aggregation.get(
        '/api/v1/projects',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert len(data['projects']) >= 1
    
    # Find the test project in the list
    test_project_found = False
    for project in data['projects']:
        if project['id'] == test_project.id:
            test_project_found = True
            assert project['name'] == test_project.name
            assert project['description'] == test_project.description
            break
    
    assert test_project_found is True

def test_update_project_api(client_data_aggregation, auth_token, test_project):
    """Test the update project API endpoint."""
    # Update the project
    response = client_data_aggregation.put(
        f'/api/v1/projects/{test_project.id}',
        json={
            'name': 'Updated Test Project',
            'description': 'An updated test project'
        },
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['project']['id'] == test_project.id
    assert data['project']['name'] == 'Updated Test Project'
    assert data['project']['description'] == 'An updated test project'

def test_delete_project_api(client_data_aggregation, auth_token, test_project):
    """Test the delete project API endpoint."""
    # Delete the project
    response = client_data_aggregation.delete(
        f'/api/v1/projects/{test_project.id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Check that the project was deleted
    response = client_data_aggregation.get(
        f'/api/v1/projects/{test_project.id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the project is not found
    assert response.status_code == 404

def test_add_user_to_project_api(client_data_aggregation, auth_token, test_project):
    """Test the add user to project API endpoint."""
    # Create a new user
    from mcps.data_aggregation.src.models.user import User, Role, db
    
    with client_data_aggregation.application.app_context():
        user = User(
            username='projectuser',
            email='projectuser@example.com',
            role=Role.USER
        )
        user.set_password('projectpassword')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
    
    # Add the user to the project
    response = client_data_aggregation.post(
        f'/api/v1/projects/{test_project.id}/users',
        json={
            'user_id': user_id,
            'role': 'VIEWER'
        },
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 201
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Check that the user was added to the project
    response = client_data_aggregation.get(
        f'/api/v1/projects/{test_project.id}/users',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    
    # Check that the response is successful
    assert response.status_code == 200
    
    # Check that the response contains the expected data
    data = json.loads(response.data)
    assert data['success'] is True
    
    # Find the added user in the list
    user_found = False
    for user in data['users']:
        if user['user_id'] == user_id:
            user_found = True
            assert user['username'] == 'projectuser'
            assert user['role'] == 'VIEWER'
            break
    
    assert user_found is True

