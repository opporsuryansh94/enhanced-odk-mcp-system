"""
Test configuration and fixtures for ODK MCP System tests.
"""

import os
import sys
import pytest
import tempfile
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import MCP modules
from mcps.form_management.src.models.form import db as form_db, Form
from mcps.data_collection.src.models.submission import db as submission_db, Submission
from mcps.data_aggregation.src.models.user import db as user_db, User, Project, Role, UserProject

# Import agent modules
# (These would be imported here if needed)

@pytest.fixture
def app_form_management():
    """Create a Flask test client for the Form Management MCP."""
    from mcps.form_management.src.main import create_app
    
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'JWT_SECRET_KEY': 'test_secret_key'
    })
    
    # Create the database and the tables
    with app.app_context():
        form_db.create_all()
    
    yield app
    
    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client_form_management(app_form_management):
    """Create a test client for the Form Management MCP."""
    return app_form_management.test_client()

@pytest.fixture
def app_data_collection():
    """Create a Flask test client for the Data Collection MCP."""
    from mcps.data_collection.src.main import create_app
    
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'JWT_SECRET_KEY': 'test_secret_key'
    })
    
    # Create the database and the tables
    with app.app_context():
        submission_db.create_all()
    
    yield app
    
    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client_data_collection(app_data_collection):
    """Create a test client for the Data Collection MCP."""
    return app_data_collection.test_client()

@pytest.fixture
def app_data_aggregation():
    """Create a Flask test client for the Data Aggregation MCP."""
    from mcps.data_aggregation.src.main import create_app
    
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'JWT_SECRET_KEY': 'test_secret_key'
    })
    
    # Create the database and the tables
    with app.app_context():
        user_db.create_all()
    
    yield app
    
    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client_data_aggregation(app_data_aggregation):
    """Create a test client for the Data Aggregation MCP."""
    return app_data_aggregation.test_client()

@pytest.fixture
def auth_token(app_data_aggregation):
    """Create an authentication token for testing."""
    from flask_jwt_extended import create_access_token
    
    with app_data_aggregation.app_context():
        # Create a test user
        user = User(
            username='testuser',
            email='test@example.com',
            role=Role.ADMIN
        )
        user.set_password('testpassword')
        user_db.session.add(user)
        user_db.session.commit()
        
        # Create an access token
        access_token = create_access_token(identity=user.id)
    
    return access_token

@pytest.fixture
def test_project(app_data_aggregation, auth_token):
    """Create a test project for testing."""
    with app_data_aggregation.app_context():
        # Get the user
        user = User.query.filter_by(username='testuser').first()
        
        # Create a test project
        project = Project(
            name='Test Project',
            description='A test project',
            created_by=user.id
        )
        user_db.session.add(project)
        user_db.session.commit()
        
        # Associate the user with the project
        user_project = UserProject(
            user_id=user.id,
            project_id=project.id,
            role=Role.ADMIN
        )
        user_db.session.add(user_project)
        user_db.session.commit()
    
    return project

@pytest.fixture
def test_form(app_form_management, test_project):
    """Create a test form for testing."""
    with app_form_management.app_context():
        # Create a test form
        form = Form(
            name='Test Form',
            project_id=test_project.id,
            version='1.0',
            created_by='testuser',
            xml_content='<form>Test Form</form>',
            json_schema='{"type": "object"}'
        )
        form_db.session.add(form)
        form_db.session.commit()
    
    return form

@pytest.fixture
def test_submission(app_data_collection, test_form):
    """Create a test submission for testing."""
    with app_data_collection.app_context():
        # Create a test submission
        submission = Submission(
            form_id=test_form.id,
            project_id=test_form.project_id,
            submitted_by='testuser',
            data='{"field1": "value1", "field2": "value2"}'
        )
        submission_db.session.add(submission)
        submission_db.session.commit()
    
    return submission

@pytest.fixture
def test_xlsform():
    """Create a test XLSForm for testing."""
    # Create a temporary XLSForm file
    import pandas as pd
    
    # Create a simple XLSForm with survey, choices, and settings sheets
    survey_data = {
        'type': ['text', 'select_one gender', 'integer'],
        'name': ['name', 'gender', 'age'],
        'label': ['What is your name?', 'What is your gender?', 'How old are you?']
    }
    
    choices_data = {
        'list_name': ['gender', 'gender'],
        'name': ['male', 'female'],
        'label': ['Male', 'Female']
    }
    
    settings_data = {
        'form_title': ['Test Form'],
        'form_id': ['test_form']
    }
    
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Create the XLSForm file
        xlsform_path = os.path.join(tmpdirname, 'test_form.xlsx')
        
        # Create the Excel writer
        with pd.ExcelWriter(xlsform_path) as writer:
            pd.DataFrame(survey_data).to_excel(writer, sheet_name='survey', index=False)
            pd.DataFrame(choices_data).to_excel(writer, sheet_name='choices', index=False)
            pd.DataFrame(settings_data).to_excel(writer, sheet_name='settings', index=False)
        
        yield xlsform_path

