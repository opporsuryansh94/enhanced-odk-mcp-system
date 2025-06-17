"""
Projects page for the ODK MCP System Streamlit UI.

This module renders the projects page of the application, allowing users to
create, view, and manage projects.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

import config
import utils

def render():
    """Render the projects page."""
    st.markdown('<h1 class="main-header">Projects</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Create and manage data collection projects</p>', unsafe_allow_html=True)
    
    # Initialize projects_action if not exists
    if "projects_action" not in st.session_state:
        st.session_state.projects_action = "list"
    
    # Handle different actions
    action = st.session_state.projects_action
    
    if action == "create":
        render_create_project()
    elif action == "view":
        render_view_project()
    else:  # Default to list
        render_list_projects()

def render_list_projects():
    """Render the list of projects."""
    # Create project button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Create New Project", key="create_project_btn"):
            st.session_state.projects_action = "create"
            st.experimental_rerun()
    
    # In a real implementation, we would make an API call to get the list of projects
    # For now, we'll use simulated data
    
    # Check if we have a token
    token = st.session_state.token
    if not token:
        st.warning("Authentication token not found. Please sign in again.")
        return
    
    # Try to get projects from the API
    success, projects = utils.get_projects(token, config.DATA_AGGREGATION_API)
    
    if not success:
        # If API call fails, use simulated data
        st.warning(f"Could not fetch projects from API: {projects}")
        st.info("Using simulated data for demonstration purposes.")
        
        # Simulated projects data
        projects = [
            {
                "id": "project1",
                "name": "Health Survey 2023",
                "description": "Annual health survey for rural communities",
                "created_at": "2023-01-15T10:30:00Z",
                "created_by": "admin",
                "form_count": 3,
                "submission_count": 120
            },
            {
                "id": "project2",
                "name": "Education Assessment",
                "description": "Assessment of educational facilities and outcomes",
                "created_at": "2023-02-20T14:45:00Z",
                "created_by": "admin",
                "form_count": 2,
                "submission_count": 85
            },
            {
                "id": "project3",
                "name": "Water Access Survey",
                "description": "Survey of water access and quality in target communities",
                "created_at": "2023-03-10T09:15:00Z",
                "created_by": "analyst",
                "form_count": 1,
                "submission_count": 42
            }
        ]
    
    # Display projects
    if not projects:
        st.info("No projects found. Create a new project to get started.")
    else:
        st.markdown(f"### Found {len(projects)} projects")
        
        # Display projects in cards
        for project in projects:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                <div class="project-card">
                    <h3>{project.get('name', 'Unnamed Project')}</h3>
                    <p>{project.get('description', 'No description')}</p>
                    <p><small>Created: {utils.format_timestamp(project.get('created_at', ''))}</small></p>
                    <p><small>Forms: {project.get('form_count', 0)} | Submissions: {project.get('submission_count', 0)}</small></p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Select project button
                if st.button("Select", key=f"select_project_{project.get('id')}"):
                    utils.set_current_project(
                        project_id=project.get('id'),
                        project_name=project.get('name')
                    )
                    st.session_state.projects_action = "view"
                    st.experimental_rerun()

def render_create_project():
    """Render the create project form."""
    st.markdown("### Create New Project")
    
    # Project form
    with st.form("create_project_form"):
        project_name = st.text_input("Project Name", max_chars=100)
        project_description = st.text_area("Project Description", max_chars=500)
        
        # Submit button
        submitted = st.form_submit_button("Create Project")
        
        if submitted:
            if not project_name:
                st.error("Project name is required")
                return
            
            # In a real implementation, we would make an API call to create the project
            token = st.session_state.token
            if not token:
                st.warning("Authentication token not found. Please sign in again.")
                return
            
            # Try to create project via API
            success, response = utils.create_project(
                token=token,
                api_url=config.DATA_AGGREGATION_API,
                project_name=project_name,
                project_description=project_description
            )
            
            if success:
                st.success(f"Project '{project_name}' created successfully!")
                
                # Set as current project
                project_id = response.get('project_id', 'project1')  # Fallback for demo
                utils.set_current_project(
                    project_id=project_id,
                    project_name=project_name
                )
                
                # Switch to view project
                st.session_state.projects_action = "view"
                st.experimental_rerun()
            else:
                st.error(f"Failed to create project: {response}")
                st.info("Using simulated data for demonstration purposes.")
                
                # Simulate successful creation for demo
                utils.set_current_project(
                    project_id="project1",
                    project_name=project_name
                )
                
                # Switch to view project
                st.session_state.projects_action = "view"
                st.experimental_rerun()
    
    # Cancel button
    if st.button("Cancel", key="cancel_create_project"):
        st.session_state.projects_action = "list"
        st.experimental_rerun()

def render_view_project():
    """Render the view project page."""
    # Get current project
    current_project = st.session_state.current_project
    if not current_project:
        st.warning("No project selected")
        st.session_state.projects_action = "list"
        st.experimental_rerun()
        return
    
    # Display project details
    st.markdown(f"### Project: {current_project.get('name', 'Unnamed Project')}")
    
    # In a real implementation, we would make an API call to get the project details
    # For now, we'll use simulated data
    
    # Check if we have a token
    token = st.session_state.token
    if not token:
        st.warning("Authentication token not found. Please sign in again.")
        return
    
    # Project tabs
    tab1, tab2, tab3 = st.tabs(["Overview", "Forms", "Data"])
    
    with tab1:
        # Project overview
        st.markdown("#### Project Overview")
        
        # Simulated project details
        project_details = {
            "id": current_project.get('id', 'unknown'),
            "name": current_project.get('name', 'Unnamed Project'),
            "description": "Sample project description. This would be fetched from the API in a real implementation.",
            "created_at": "2023-01-15T10:30:00Z",
            "created_by": "admin",
            "form_count": 3,
            "submission_count": 120,
            "last_submission": "2023-04-10T15:20:00Z"
        }
        
        # Display project details
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **Project ID:** {project_details['id']}  
            **Name:** {project_details['name']}  
            **Description:** {project_details['description']}  
            """)
        
        with col2:
            st.markdown(f"""
            **Created:** {utils.format_timestamp(project_details['created_at'])}  
            **Created By:** {project_details['created_by']}  
            **Last Submission:** {utils.format_timestamp(project_details['last_submission'])}  
            """)
        
        # Project statistics
        st.markdown("#### Project Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Forms", project_details['form_count'])
        
        with col2:
            st.metric("Submissions", project_details['submission_count'])
        
        with col3:
            st.metric("Completion Rate", "85%")
        
        # Recent activity
        st.markdown("#### Recent Activity")
        
        # Simulated activity data
        activity_data = {
            "timestamp": [
                "2023-04-10T15:20:00Z",
                "2023-04-10T14:45:00Z",
                "2023-04-10T12:30:00Z",
                "2023-04-09T16:15:00Z",
                "2023-04-09T10:00:00Z"
            ],
            "user": ["collector1", "collector2", "admin", "collector1", "analyst"],
            "action": [
                "Submitted data for Form 1",
                "Submitted data for Form 2",
                "Updated Form 1",
                "Submitted data for Form 3",
                "Generated report"
            ]
        }
        
        activity_df = pd.DataFrame(activity_data)
        activity_df["timestamp"] = activity_df["timestamp"].apply(utils.format_timestamp)
        
        st.dataframe(activity_df, use_container_width=True)
    
    with tab2:
        # Forms tab
        st.markdown("#### Project Forms")
        
        # Try to get forms from the API
        success, forms = utils.get_forms(token, config.FORM_MANAGEMENT_API, current_project.get('id'))
        
        if not success:
            # If API call fails, use simulated data
            st.warning(f"Could not fetch forms from API: {forms}")
            st.info("Using simulated data for demonstration purposes.")
            
            # Simulated forms data
            forms = [
                {
                    "id": "form1",
                    "name": "Health Assessment Form",
                    "version": "1.2",
                    "created_at": "2023-01-20T11:30:00Z",
                    "submission_count": 45
                },
                {
                    "id": "form2",
                    "name": "Household Survey",
                    "version": "2.0",
                    "created_at": "2023-02-05T09:15:00Z",
                    "submission_count": 38
                },
                {
                    "id": "form3",
                    "name": "Water Quality Test",
                    "version": "1.0",
                    "created_at": "2023-03-12T14:00:00Z",
                    "submission_count": 37
                }
            ]
        
        # Display forms
        if not forms:
            st.info("No forms found in this project. Go to the Forms page to create one.")
        else:
            for form in forms:
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"""
                    <div class="form-card">
                        <h4>{form.get('name', 'Unnamed Form')}</h4>
                        <p><small>Version: {form.get('version', '1.0')} | Created: {utils.format_timestamp(form.get('created_at', ''))}</small></p>
                        <p><small>Submissions: {form.get('submission_count', 0)}</small></p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # Select form button
                    if st.button("Select", key=f"select_form_{form.get('id')}"):
                        utils.set_current_form(
                            form_id=form.get('id'),
                            form_name=form.get('name')
                        )
                        st.session_state.page = "forms"
                        st.experimental_rerun()
        
        # Create form button
        if st.button("Create New Form", key="create_form_btn"):
            st.session_state.page = "forms"
            st.session_state.forms_action = "upload"
            st.experimental_rerun()
    
    with tab3:
        # Data tab
        st.markdown("#### Project Data")
        
        # Try to get submissions from the API
        success, submissions = utils.get_submissions(token, config.DATA_AGGREGATION_API, current_project.get('id'))
        
        if not success:
            # If API call fails, use simulated data
            st.warning(f"Could not fetch submissions from API: {submissions}")
            st.info("Using simulated data for demonstration purposes.")
            
            # Simulated submissions data (simplified)
            submissions = [
                {"id": "sub1", "form_id": "form1", "submitted_at": "2023-04-10T15:20:00Z", "submitted_by": "collector1"},
                {"id": "sub2", "form_id": "form2", "submitted_at": "2023-04-10T14:45:00Z", "submitted_by": "collector2"},
                {"id": "sub3", "form_id": "form1", "submitted_at": "2023-04-09T16:15:00Z", "submitted_by": "collector1"},
                {"id": "sub4", "form_id": "form3", "submitted_at": "2023-04-09T10:00:00Z", "submitted_by": "collector3"},
                {"id": "sub5", "form_id": "form2", "submitted_at": "2023-04-08T11:30:00Z", "submitted_by": "collector2"}
            ]
        
        # Display submissions
        if not submissions:
            st.info("No data submissions found in this project.")
        else:
            # Create a DataFrame for display
            submissions_df = pd.DataFrame(submissions)
            
            # Format timestamp if it exists
            if "submitted_at" in submissions_df.columns:
                submissions_df["submitted_at"] = submissions_df["submitted_at"].apply(utils.format_timestamp)
            
            st.dataframe(submissions_df, use_container_width=True)
        
        # Analyze data button
        if st.button("Analyze Data", key="analyze_data_btn"):
            st.session_state.page = "data_analysis"
            st.experimental_rerun()
    
    # Back button
    if st.button("Back to Projects List", key="back_to_projects"):
        st.session_state.projects_action = "list"
        st.experimental_rerun()

