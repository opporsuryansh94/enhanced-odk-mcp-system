"""
Settings page for the ODK MCP System Streamlit UI.

This module renders the settings page of the application, allowing users to
manage their account settings, configure system preferences, and manage API integrations.
"""

import streamlit as st
import pandas as pd
import json
import io
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime

import config
import utils

def render():
    """Render the settings page."""
    st.markdown('<h1 class="main-header">Settings</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Manage your account and system settings</p>', unsafe_allow_html=True)
    
    # Check if user is authenticated
    if not st.session_state.token:
        st.warning("Please sign in to access settings")
        return
    
    # Settings tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Account", "System", "Integrations", "API Keys"])
    
    with tab1:
        render_account_settings()
    
    with tab2:
        render_system_settings()
    
    with tab3:
        render_integration_settings()
    
    with tab4:
        render_api_key_settings()

def render_account_settings():
    """Render account settings."""
    st.markdown("### Account Settings")
    
    # Get current user info
    username = st.session_state.username
    
    # Display current user info
    st.markdown(f"**Username:** {username}")
    
    # Change password form
    st.markdown("#### Change Password")
    
    with st.form("change_password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        submitted = st.form_submit_button("Change Password")
        
        if submitted:
            if not current_password:
                st.error("Please enter your current password")
            elif not new_password:
                st.error("Please enter a new password")
            elif new_password != confirm_password:
                st.error("New passwords do not match")
            else:
                # In a real implementation, we would make an API call to change the password
                # For now, we'll simulate a successful password change
                st.success("Password changed successfully")
    
    # Profile information form
    st.markdown("#### Profile Information")
    
    with st.form("profile_info_form"):
        full_name = st.text_input("Full Name", value="John Doe")
        email = st.text_input("Email", value="john.doe@example.com")
        organization = st.text_input("Organization", value="Example NGO")
        role = st.selectbox("Role", ["Admin", "Project Manager", "Data Collector", "Analyst"], index=0)
        
        submitted = st.form_submit_button("Update Profile")
        
        if submitted:
            # In a real implementation, we would make an API call to update the profile
            # For now, we'll simulate a successful profile update
            st.success("Profile updated successfully")
    
    # Delete account button
    st.markdown("#### Delete Account")
    st.warning("Deleting your account is permanent and cannot be undone.")
    
    if st.button("Delete Account", key="delete_account"):
        # In a real implementation, we would show a confirmation dialog
        # For now, we'll simulate a confirmation
        st.error("Account deletion is disabled in this demo")

def render_system_settings():
    """Render system settings."""
    st.markdown("### System Settings")
    
    # Theme settings
    st.markdown("#### Theme")
    
    theme = st.selectbox(
        "Select Theme",
        ["Light", "Dark", "System Default"],
        index=2
    )
    
    if st.button("Apply Theme", key="apply_theme"):
        st.success(f"Theme set to {theme}")
    
    # Language settings
    st.markdown("#### Language")
    
    language = st.selectbox(
        "Select Language",
        ["English", "Spanish", "French", "German", "Chinese", "Arabic"],
        index=0
    )
    
    if st.button("Apply Language", key="apply_language"):
        st.success(f"Language set to {language}")
    
    # Notification settings
    st.markdown("#### Notifications")
    
    email_notifications = st.checkbox("Email Notifications", value=True)
    browser_notifications = st.checkbox("Browser Notifications", value=True)
    
    notification_types = st.multiselect(
        "Notification Types",
        ["Form Submissions", "Report Generation", "System Updates", "User Activity"],
        default=["Form Submissions", "Report Generation"]
    )
    
    if st.button("Save Notification Settings", key="save_notifications"):
        st.success("Notification settings saved")
    
    # Data storage settings
    st.markdown("#### Data Storage")
    
    storage_location = st.selectbox(
        "Default Storage Location",
        ["Local SQLite", "Baserow", "Custom Database"],
        index=0
    )
    
    if storage_location == "Custom Database":
        db_connection_string = st.text_input("Database Connection String")
    
    data_retention = st.slider("Data Retention Period (days)", 30, 365, 90)
    
    if st.button("Save Storage Settings", key="save_storage"):
        st.success("Storage settings saved")

def render_integration_settings():
    """Render integration settings."""
    st.markdown("### Integration Settings")
    
    # Baserow integration
    st.markdown("#### Baserow Integration")
    
    baserow_enabled = st.checkbox("Enable Baserow Integration", value=False)
    
    if baserow_enabled:
        baserow_url = st.text_input("Baserow URL", value="https://api.baserow.io")
        baserow_api_key = st.text_input("Baserow API Key", type="password")
        
        # Test connection button
        if st.button("Test Baserow Connection", key="test_baserow"):
            with st.spinner("Testing connection..."):
                # In a real implementation, we would make an API call to test the connection
                # For now, we'll simulate a successful connection
                st.success("Successfully connected to Baserow")
    
    # Save Baserow settings button
    if st.button("Save Baserow Settings", key="save_baserow"):
        if baserow_enabled and (not baserow_url or not baserow_api_key):
            st.error("Please enter Baserow URL and API Key")
        else:
            st.success("Baserow settings saved")
    
    # AI tool integration
    st.markdown("#### AI Tool Integration")
    
    ai_tool = st.selectbox(
        "Select AI Tool",
        ["Claude", "ChatGPT", "Other"],
        index=0
    )
    
    if ai_tool == "Claude":
        claude_api_key = st.text_input("Claude API Key", type="password")
        claude_model = st.selectbox(
            "Claude Model",
            ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            index=1
        )
    elif ai_tool == "ChatGPT":
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        openai_model = st.selectbox(
            "OpenAI Model",
            ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            index=1
        )
    else:
        custom_ai_url = st.text_input("API URL")
        custom_ai_key = st.text_input("API Key", type="password")
    
    # Save AI tool settings button
    if st.button("Save AI Tool Settings", key="save_ai_tool"):
        st.success(f"{ai_tool} integration settings saved")

def render_api_key_settings():
    """Render API key settings."""
    st.markdown("### API Keys")
    
    st.markdown("""
    API keys allow you to integrate the ODK MCP System with external applications.
    You can generate API keys for different purposes and manage their permissions.
    """)
    
    # List existing API keys
    st.markdown("#### Existing API Keys")
    
    # Simulated API keys
    api_keys = [
        {
            "id": "key1",
            "name": "Development Key",
            "created_at": "2023-03-15T10:30:00Z",
            "last_used": "2023-04-10T14:20:00Z",
            "permissions": ["read:forms", "read:submissions"]
        },
        {
            "id": "key2",
            "name": "Production Key",
            "created_at": "2023-03-20T15:45:00Z",
            "last_used": "2023-04-15T09:10:00Z",
            "permissions": ["read:forms", "read:submissions", "write:submissions"]
        }
    ]
    
    if not api_keys:
        st.info("No API keys found. Generate a new key to get started.")
    else:
        for key in api_keys:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                <div class="api-key-card">
                    <h4>{key.get('name', 'Unnamed Key')}</h4>
                    <p><small>Created: {utils.format_timestamp(key.get('created_at', ''))} | Last Used: {utils.format_timestamp(key.get('last_used', ''))}</small></p>
                    <p><small>Permissions: {', '.join(key.get('permissions', []))}</small></p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Revoke key button
                if st.button("Revoke", key=f"revoke_key_{key.get('id')}"):
                    # In a real implementation, we would make an API call to revoke the key
                    # For now, we'll simulate a successful revocation
                    st.success(f"API key '{key.get('name')}' revoked successfully")
    
    # Generate new API key
    st.markdown("#### Generate New API Key")
    
    with st.form("generate_api_key_form"):
        key_name = st.text_input("Key Name", max_chars=100)
        
        st.markdown("##### Permissions")
        read_forms = st.checkbox("Read Forms", value=True)
        write_forms = st.checkbox("Write Forms", value=False)
        read_submissions = st.checkbox("Read Submissions", value=True)
        write_submissions = st.checkbox("Write Submissions", value=False)
        read_reports = st.checkbox("Read Reports", value=True)
        write_reports = st.checkbox("Write Reports", value=False)
        
        expiration = st.selectbox(
            "Expiration",
            ["Never", "30 days", "90 days", "1 year"],
            index=2
        )
        
        submitted = st.form_submit_button("Generate API Key")
        
        if submitted:
            if not key_name:
                st.error("Please enter a key name")
            else:
                # In a real implementation, we would make an API call to generate the key
                # For now, we'll simulate a successful key generation
                
                # Collect permissions
                permissions = []
                if read_forms:
                    permissions.append("read:forms")
                if write_forms:
                    permissions.append("write:forms")
                if read_submissions:
                    permissions.append("read:submissions")
                if write_submissions:
                    permissions.append("write:submissions")
                if read_reports:
                    permissions.append("read:reports")
                if write_reports:
                    permissions.append("write:reports")
                
                # Display the generated key
                st.success(f"API key '{key_name}' generated successfully")
                
                # Simulated API key
                api_key = "odk_mcp_" + "".join([chr(ord('a') + i % 26) for i in range(32)])
                
                st.code(api_key)
                st.warning("Make sure to copy this key now. You won't be able to see it again!")
                
                # Copy button
                if st.button("Copy to Clipboard", key="copy_api_key"):
                    st.success("API key copied to clipboard")

