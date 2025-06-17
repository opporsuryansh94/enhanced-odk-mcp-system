"""
ODK MCP System Streamlit UI

This is the main application file for the ODK MCP System Streamlit UI.
It handles authentication, navigation, and page rendering.
"""

import streamlit as st
import pandas as pd
import json
import io
import base64
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import configuration and utilities
import config
import utils

# Import pages
from pages import home, projects, forms, data_collection, data_analysis, reports, settings

# Page configuration
st.set_page_config(
    page_title="ODK MCP System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    with open(os.path.join(os.path.dirname(__file__), "styles.css")) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if "token" not in st.session_state:
        st.session_state.token = None
    
    if "username" not in st.session_state:
        st.session_state.username = None
    
    if "page" not in st.session_state:
        st.session_state.page = "home"
    
    if "current_project" not in st.session_state:
        st.session_state.current_project = None
    
    if "current_form" not in st.session_state:
        st.session_state.current_form = None

# Authentication
def authenticate(username: str, password: str) -> bool:
    """Authenticate user with username and password."""
    # In a real implementation, we would make an API call to authenticate
    # For now, we'll use simulated data
    
    # Try to authenticate via API
    success, response = utils.authenticate_user(
        username=username,
        password=password,
        api_url=config.DATA_AGGREGATION_API
    )
    
    if success:
        st.session_state.authenticated = True
        st.session_state.token = response.get("token")
        st.session_state.username = username
        return True
    else:
        # If API call fails, use simulated data
        st.warning(f"Could not authenticate via API: {response}")
        st.info("Using simulated authentication for demonstration purposes.")
        
        # Check against default users
        try:
            with open(os.path.join(os.path.dirname(__file__), "default_users.json")) as f:
                default_users = json.load(f)
                
                if username in default_users["credentials"] and password == default_users["credentials"][username]:
                    st.session_state.authenticated = True
                    st.session_state.token = "simulated_token_" + username
                    st.session_state.username = username
                    return True
        except Exception as e:
            st.error(f"Error loading default users: {e}")
        
        return False

def logout():
    """Log out the current user."""
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.current_project = None
    st.session_state.current_form = None
    st.session_state.page = "home"

# Render login form
def render_login():
    """Render the login form."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-header">', unsafe_allow_html=True)
    st.markdown('<h1>ODK MCP System</h1>', unsafe_allow_html=True)
    st.markdown('<p>Sign in to continue</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        submitted = st.form_submit_button("Sign In")
        
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                if authenticate(username, password):
                    st.success("Authentication successful!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password")
    
    st.markdown('<div class="login-footer">', unsafe_allow_html=True)
    st.markdown('<p>For demo purposes, use username: <strong>admin</strong> and password: <strong>password</strong></p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Render sidebar
def render_sidebar():
    """Render the sidebar."""
    with st.sidebar:
        st.markdown('<div class="sidebar-header">', unsafe_allow_html=True)
        st.markdown('<h3>ODK MCP System</h3>', unsafe_allow_html=True)
        st.markdown(f'<p>Welcome, {st.session_state.username}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Navigation
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h4>Navigation</h4>', unsafe_allow_html=True)
        
        if st.button("Home", key="nav_home"):
            st.session_state.page = "home"
            st.experimental_rerun()
        
        if st.button("Projects", key="nav_projects"):
            st.session_state.page = "projects"
            st.experimental_rerun()
        
        if st.button("Forms", key="nav_forms"):
            st.session_state.page = "forms"
            st.experimental_rerun()
        
        if st.button("Data Collection", key="nav_data_collection"):
            st.session_state.page = "data_collection"
            st.experimental_rerun()
        
        if st.button("Data Analysis", key="nav_data_analysis"):
            st.session_state.page = "data_analysis"
            st.experimental_rerun()
        
        if st.button("Reports", key="nav_reports"):
            st.session_state.page = "reports"
            st.experimental_rerun()
        
        if st.button("Settings", key="nav_settings"):
            st.session_state.page = "settings"
            st.experimental_rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Current context
        if st.session_state.current_project:
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown('<h4>Current Project</h4>', unsafe_allow_html=True)
            st.markdown(f'<p>{st.session_state.current_project.get("name", "Unnamed Project")}</p>', unsafe_allow_html=True)
            
            if st.button("Change Project", key="change_project"):
                st.session_state.current_project = None
                st.session_state.current_form = None
                st.session_state.page = "projects"
                st.experimental_rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        if st.session_state.current_form:
            st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
            st.markdown('<h4>Current Form</h4>', unsafe_allow_html=True)
            st.markdown(f'<p>{st.session_state.current_form.get("name", "Unnamed Form")}</p>', unsafe_allow_html=True)
            
            if st.button("Change Form", key="change_form"):
                st.session_state.current_form = None
                st.session_state.page = "forms"
                st.experimental_rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Sign out
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        if st.button("Sign Out", key="sign_out"):
            logout()
            st.experimental_rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Footer
        st.markdown('<div class="footer">', unsafe_allow_html=True)
        st.markdown('<p>ODK MCP System v1.0</p>', unsafe_allow_html=True)
        st.markdown('<p>&copy; 2023 ODK MCP Team</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# Render content
def render_content():
    """Render the main content based on the current page."""
    page = st.session_state.page
    
    if page == "home":
        home.render()
    elif page == "projects":
        projects.render()
    elif page == "forms":
        forms.render()
    elif page == "data_collection":
        data_collection.render()
    elif page == "data_analysis":
        data_analysis.render()
    elif page == "reports":
        reports.render()
    elif page == "settings":
        settings.render()
    else:
        st.error(f"Unknown page: {page}")
        st.session_state.page = "home"
        st.experimental_rerun()

# Main function
def main():
    """Main function to run the Streamlit app."""
    # Load custom CSS
    load_css()
    
    # Initialize session state
    initialize_session_state()
    
    # Check authentication
    if not st.session_state.authenticated:
        render_login()
    else:
        # Render sidebar
        render_sidebar()
        
        # Render content
        render_content()

if __name__ == "__main__":
    main()

