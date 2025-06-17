"""
Utility functions for the ODK MCP System Streamlit UI.

This module provides utility functions for API communication, authentication,
data processing, and UI components.
"""

import os
import json
import logging
import requests
import pandas as pd
import streamlit as st
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import base64
import io
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Communication Functions

def api_request(
    method: str,
    url: str,
    token: Optional[str] = None,
    params: Optional[Dict] = None,
    data: Optional[Dict] = None,
    files: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    timeout: int = 30
) -> Tuple[bool, Union[Dict, str]]:
    """
    Make an API request to an MCP endpoint.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        url: API endpoint URL
        token: Authentication token
        params: URL parameters
        data: Form data
        files: Files to upload
        json_data: JSON data
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (success, response_data)
    """
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            files=files,
            json=json_data,
            timeout=timeout
        )
        
        # Try to parse JSON response
        try:
            response_data = response.json()
        except:
            response_data = response.text
        
        # Check if request was successful
        if response.status_code >= 200 and response.status_code < 300:
            return True, response_data
        else:
            error_msg = response_data if isinstance(response_data, dict) else f"Error: {response.status_code} - {response.text}"
            return False, error_msg
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        return False, f"Connection error: {str(e)}"

def login_user(username: str, password: str, api_url: str) -> Tuple[bool, Union[Dict, str]]:
    """
    Authenticate user with the Data Aggregation MCP.
    
    Args:
        username: User's username
        password: User's password
        api_url: API endpoint URL
        
    Returns:
        Tuple of (success, response_data)
    """
    login_url = f"{api_url}/auth/login"
    return api_request(
        method="POST",
        url=login_url,
        json_data={"username": username, "password": password}
    )

def get_projects(token: str, api_url: str) -> Tuple[bool, Union[List[Dict], str]]:
    """
    Get list of projects from the Data Aggregation MCP.
    
    Args:
        token: Authentication token
        api_url: API endpoint URL
        
    Returns:
        Tuple of (success, projects_list)
    """
    projects_url = f"{api_url}/projects"
    success, response = api_request(
        method="GET",
        url=projects_url,
        token=token
    )
    
    if success and isinstance(response, dict) and "projects" in response:
        return True, response["projects"]
    else:
        return success, response

def get_forms(token: str, api_url: str, project_id: str) -> Tuple[bool, Union[List[Dict], str]]:
    """
    Get list of forms for a project from the Form Management MCP.
    
    Args:
        token: Authentication token
        api_url: API endpoint URL
        project_id: Project ID
        
    Returns:
        Tuple of (success, forms_list)
    """
    forms_url = f"{api_url}/projects/{project_id}/forms"
    success, response = api_request(
        method="GET",
        url=forms_url,
        token=token
    )
    
    if success and isinstance(response, dict) and "forms" in response:
        return True, response["forms"]
    else:
        return success, response

def get_submissions(token: str, api_url: str, project_id: str, form_id: Optional[str] = None) -> Tuple[bool, Union[List[Dict], str]]:
    """
    Get list of submissions for a project/form from the Data Aggregation MCP.
    
    Args:
        token: Authentication token
        api_url: API endpoint URL
        project_id: Project ID
        form_id: Form ID (optional)
        
    Returns:
        Tuple of (success, submissions_list)
    """
    submissions_url = f"{api_url}/projects/{project_id}/data"
    params = {}
    if form_id:
        params["form_id"] = form_id
        
    success, response = api_request(
        method="GET",
        url=submissions_url,
        token=token,
        params=params
    )
    
    if success and isinstance(response, dict) and "data" in response:
        return True, response["data"]
    else:
        return success, response

def upload_form(token: str, api_url: str, project_id: str, form_file, form_name: str) -> Tuple[bool, Union[Dict, str]]:
    """
    Upload a form to the Form Management MCP.
    
    Args:
        token: Authentication token
        api_url: API endpoint URL
        project_id: Project ID
        form_file: Form file (XLSForm)
        form_name: Form name
        
    Returns:
        Tuple of (success, response_data)
    """
    upload_url = f"{api_url}/projects/{project_id}/forms"
    files = {"file": form_file}
    data = {"name": form_name}
    
    return api_request(
        method="POST",
        url=upload_url,
        token=token,
        data=data,
        files=files
    )

def create_project(token: str, api_url: str, project_name: str, project_description: str) -> Tuple[bool, Union[Dict, str]]:
    """
    Create a new project in the Data Aggregation MCP.
    
    Args:
        token: Authentication token
        api_url: API endpoint URL
        project_name: Project name
        project_description: Project description
        
    Returns:
        Tuple of (success, response_data)
    """
    create_url = f"{api_url}/projects"
    json_data = {
        "name": project_name,
        "description": project_description
    }
    
    return api_request(
        method="POST",
        url=create_url,
        token=token,
        json_data=json_data
    )

def run_data_analysis(token: str, api_url: str, project_id: str, form_id: Optional[str], analysis_type: str, analysis_config: Dict) -> Tuple[bool, Union[Dict, str]]:
    """
    Run a data analysis task on the Data Aggregation MCP.
    
    Args:
        token: Authentication token
        api_url: API endpoint URL
        project_id: Project ID
        form_id: Form ID (optional)
        analysis_type: Type of analysis (descriptive, inferential, exploration)
        analysis_config: Analysis configuration
        
    Returns:
        Tuple of (success, response_data)
    """
    analysis_url = f"{api_url}/projects/{project_id}/analysis/{analysis_type}"
    params = {}
    if form_id:
        params["form_id"] = form_id
    
    return api_request(
        method="POST",
        url=analysis_url,
        token=token,
        params=params,
        json_data=analysis_config
    )

def generate_report(token: str, api_url: str, project_id: str, form_id: Optional[str], report_config: Dict) -> Tuple[bool, Union[Dict, str]]:
    """
    Generate a report on the Data Aggregation MCP.
    
    Args:
        token: Authentication token
        api_url: API endpoint URL
        project_id: Project ID
        form_id: Form ID (optional)
        report_config: Report configuration
        
    Returns:
        Tuple of (success, response_data)
    """
    report_url = f"{api_url}/projects/{project_id}/reports"
    params = {}
    if form_id:
        params["form_id"] = form_id
    
    return api_request(
        method="POST",
        url=report_url,
        token=token,
        params=params,
        json_data=report_config
    )

# UI Helper Functions

def display_error(message: str):
    """Display an error message in the Streamlit UI."""
    st.error(message)

def display_success(message: str):
    """Display a success message in the Streamlit UI."""
    st.success(message)

def display_info(message: str):
    """Display an info message in the Streamlit UI."""
    st.info(message)

def display_warning(message: str):
    """Display a warning message in the Streamlit UI."""
    st.warning(message)

def display_json(data: Dict):
    """Display JSON data in a formatted way."""
    st.json(data)

def display_dataframe(df: pd.DataFrame, use_container_width: bool = True):
    """Display a pandas DataFrame in the Streamlit UI."""
    st.dataframe(df, use_container_width=use_container_width)

def display_image_from_base64(base64_string: str, caption: Optional[str] = None):
    """Display an image from a base64 string."""
    try:
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        st.image(image, caption=caption, use_column_width=True)
    except Exception as e:
        st.error(f"Error displaying image: {e}")

def create_download_link(data: bytes, filename: str, text: str):
    """Create a download link for binary data."""
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{text}</a>'
    return href

def format_timestamp(timestamp: str) -> str:
    """Format a timestamp string for display."""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp

def get_color_scale(n: int) -> List[str]:
    """Get a list of n colors for charts."""
    # Default color palette
    colors = [
        "#FF4B4B",  # ODK red
        "#1E88E5",  # Blue
        "#FFC107",  # Amber
        "#4CAF50",  # Green
        "#9C27B0",  # Purple
        "#FF9800",  # Orange
        "#E91E63",  # Pink
        "#2196F3",  # Light Blue
        "#8BC34A",  # Light Green
        "#673AB7",  # Deep Purple
    ]
    
    # If we need more colors than in our palette, cycle through them
    result = []
    for i in range(n):
        result.append(colors[i % len(colors)])
    
    return result

# Session State Management

def init_session_state():
    """Initialize session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if "token" not in st.session_state:
        st.session_state.token = None
    
    if "username" not in st.session_state:
        st.session_state.username = None
    
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    
    if "current_project" not in st.session_state:
        st.session_state.current_project = None
    
    if "current_form" not in st.session_state:
        st.session_state.current_form = None

def set_authentication(authenticated: bool, token: Optional[str] = None, username: Optional[str] = None, user_info: Optional[Dict] = None):
    """Set authentication state."""
    st.session_state.authenticated = authenticated
    st.session_state.token = token
    st.session_state.username = username
    st.session_state.user_info = user_info

def clear_authentication():
    """Clear authentication state."""
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.user_info = None

def set_current_project(project_id: Optional[str], project_name: Optional[str] = None):
    """Set current project."""
    st.session_state.current_project = {
        "id": project_id,
        "name": project_name
    } if project_id else None
    
    # Clear current form when changing project
    st.session_state.current_form = None

def set_current_form(form_id: Optional[str], form_name: Optional[str] = None):
    """Set current form."""
    st.session_state.current_form = {
        "id": form_id,
        "name": form_name
    } if form_id else None

