"""
Forms page for the ODK MCP System Streamlit UI.

This module renders the forms page of the application, allowing users to
upload, view, and manage XLSForms.
"""

import streamlit as st
import pandas as pd
import io
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

import config
import utils

def render():
    """Render the forms page."""
    st.markdown('<h1 class="main-header">Forms</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload and manage XLSForms</p>', unsafe_allow_html=True)
    
    # Check if a project is selected
    current_project = st.session_state.current_project
    if not current_project:
        st.warning("Please select a project first")
        if st.button("Go to Projects"):
            st.session_state.page = "projects"
            st.experimental_rerun()
        return
    
    # Initialize forms_action if not exists
    if "forms_action" not in st.session_state:
        st.session_state.forms_action = "list"
    
    # Handle different actions
    action = st.session_state.forms_action
    
    if action == "upload":
        render_upload_form()
    elif action == "view":
        render_view_form()
    else:  # Default to list
        render_list_forms()

def render_list_forms():
    """Render the list of forms."""
    # Get current project
    current_project = st.session_state.current_project
    
    # Display project name
    st.markdown(f"### Forms in Project: {current_project.get('name', 'Unnamed Project')}")
    
    # Upload form button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Upload New Form", key="upload_form_btn"):
            st.session_state.forms_action = "upload"
            st.experimental_rerun()
    
    # In a real implementation, we would make an API call to get the list of forms
    # For now, we'll use simulated data
    
    # Check if we have a token
    token = st.session_state.token
    if not token:
        st.warning("Authentication token not found. Please sign in again.")
        return
    
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
                "updated_at": "2023-02-15T09:45:00Z",
                "created_by": "admin",
                "submission_count": 45,
                "questions_count": 25,
                "has_media": True
            },
            {
                "id": "form2",
                "name": "Household Survey",
                "version": "2.0",
                "created_at": "2023-02-05T09:15:00Z",
                "updated_at": "2023-02-05T09:15:00Z",
                "created_by": "admin",
                "submission_count": 38,
                "questions_count": 42,
                "has_media": False
            },
            {
                "id": "form3",
                "name": "Water Quality Test",
                "version": "1.0",
                "created_at": "2023-03-12T14:00:00Z",
                "updated_at": "2023-03-12T14:00:00Z",
                "created_by": "analyst",
                "submission_count": 37,
                "questions_count": 18,
                "has_media": True
            }
        ]
    
    # Display forms
    if not forms:
        st.info("No forms found in this project. Upload a new form to get started.")
    else:
        # Display forms in cards
        for form in forms:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                <div class="form-card">
                    <h3>{form.get('name', 'Unnamed Form')}</h3>
                    <p><small>Version: {form.get('version', '1.0')} | Questions: {form.get('questions_count', 0)}</small></p>
                    <p><small>Created: {utils.format_timestamp(form.get('created_at', ''))} | Updated: {utils.format_timestamp(form.get('updated_at', ''))}</small></p>
                    <p><small>Submissions: {form.get('submission_count', 0)} | Media: {'Yes' if form.get('has_media', False) else 'No'}</small></p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # View form button
                if st.button("View", key=f"view_form_{form.get('id')}"):
                    utils.set_current_form(
                        form_id=form.get('id'),
                        form_name=form.get('name')
                    )
                    st.session_state.forms_action = "view"
                    st.experimental_rerun()

def render_upload_form():
    """Render the upload form page."""
    # Get current project
    current_project = st.session_state.current_project
    
    st.markdown(f"### Upload XLSForm to Project: {current_project.get('name', 'Unnamed Project')}")
    
    # Form upload form
    with st.form("upload_form_form"):
        form_name = st.text_input("Form Name", max_chars=100)
        form_file = st.file_uploader("XLSForm File", type=["xls", "xlsx"])
        
        # Submit button
        submitted = st.form_submit_button("Upload Form")
        
        if submitted:
            if not form_name:
                st.error("Form name is required")
                return
            
            if not form_file:
                st.error("Please upload an XLSForm file")
                return
            
            # In a real implementation, we would make an API call to upload the form
            token = st.session_state.token
            if not token:
                st.warning("Authentication token not found. Please sign in again.")
                return
            
            # Try to upload form via API
            success, response = utils.upload_form(
                token=token,
                api_url=config.FORM_MANAGEMENT_API,
                project_id=current_project.get('id'),
                form_file=form_file,
                form_name=form_name
            )
            
            if success:
                st.success(f"Form '{form_name}' uploaded successfully!")
                
                # Set as current form
                form_id = response.get('form_id', 'form1')  # Fallback for demo
                utils.set_current_form(
                    form_id=form_id,
                    form_name=form_name
                )
                
                # Switch to view form
                st.session_state.forms_action = "view"
                st.experimental_rerun()
            else:
                st.error(f"Failed to upload form: {response}")
                st.info("Using simulated data for demonstration purposes.")
                
                # Simulate successful upload for demo
                utils.set_current_form(
                    form_id="form1",
                    form_name=form_name
                )
                
                # Switch to view form
                st.session_state.forms_action = "view"
                st.experimental_rerun()
    
    # Cancel button
    if st.button("Cancel", key="cancel_upload_form"):
        st.session_state.forms_action = "list"
        st.experimental_rerun()

def render_view_form():
    """Render the view form page."""
    # Get current project and form
    current_project = st.session_state.current_project
    current_form = st.session_state.current_form
    
    if not current_form:
        st.warning("No form selected")
        st.session_state.forms_action = "list"
        st.experimental_rerun()
        return
    
    # Display form details
    st.markdown(f"### Form: {current_form.get('name', 'Unnamed Form')}")
    
    # In a real implementation, we would make an API call to get the form details
    # For now, we'll use simulated data
    
    # Check if we have a token
    token = st.session_state.token
    if not token:
        st.warning("Authentication token not found. Please sign in again.")
        return
    
    # Form tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Structure", "Preview", "Submissions"])
    
    with tab1:
        # Form overview
        st.markdown("#### Form Overview")
        
        # Simulated form details
        form_details = {
            "id": current_form.get('id', 'unknown'),
            "name": current_form.get('name', 'Unnamed Form'),
            "version": "1.2",
            "created_at": "2023-01-20T11:30:00Z",
            "updated_at": "2023-02-15T09:45:00Z",
            "created_by": "admin",
            "submission_count": 45,
            "questions_count": 25,
            "has_media": True,
            "description": "This form is used to collect health assessment data from community members."
        }
        
        # Display form details
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            **Form ID:** {form_details['id']}  
            **Name:** {form_details['name']}  
            **Version:** {form_details['version']}  
            **Description:** {form_details['description']}  
            """)
        
        with col2:
            st.markdown(f"""
            **Created:** {utils.format_timestamp(form_details['created_at'])}  
            **Updated:** {utils.format_timestamp(form_details['updated_at'])}  
            **Created By:** {form_details['created_by']}  
            **Questions:** {form_details['questions_count']}  
            """)
        
        # Form statistics
        st.markdown("#### Form Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Submissions", form_details['submission_count'])
        
        with col2:
            st.metric("Completion Rate", "92%")
        
        with col3:
            st.metric("Avg. Completion Time", "8m 45s")
        
        # Form actions
        st.markdown("#### Form Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Collect Data", key="collect_data_btn"):
                st.session_state.page = "data_collection"
                st.experimental_rerun()
        
        with col2:
            if st.button("Analyze Data", key="analyze_form_data_btn"):
                st.session_state.page = "data_analysis"
                st.experimental_rerun()
        
        with col3:
            if st.button("Generate Report", key="generate_form_report_btn"):
                st.session_state.page = "reports"
                st.experimental_rerun()
    
    with tab2:
        # Form structure
        st.markdown("#### Form Structure")
        
        # Simulated form structure
        form_structure = [
            {"type": "start", "name": "start", "label": "Start"},
            {"type": "end", "name": "end", "label": "End"},
            {"type": "text", "name": "respondent_name", "label": "Respondent Name"},
            {"type": "select_one", "name": "gender", "label": "Gender", "choices": ["Male", "Female", "Other"]},
            {"type": "integer", "name": "age", "label": "Age"},
            {"type": "select_one", "name": "education", "label": "Education Level", "choices": ["None", "Primary", "Secondary", "Tertiary"]},
            {"type": "select_multiple", "name": "health_issues", "label": "Health Issues", "choices": ["Hypertension", "Diabetes", "Asthma", "None"]},
            {"type": "decimal", "name": "temperature", "label": "Body Temperature (°C)"},
            {"type": "decimal", "name": "weight", "label": "Weight (kg)"},
            {"type": "decimal", "name": "height", "label": "Height (cm)"},
            {"type": "calculate", "name": "bmi", "label": "BMI", "calculation": "weight / (height/100)^2"},
            {"type": "note", "name": "bmi_note", "label": "BMI Category", "relevant": "bmi > 0"},
            {"type": "image", "name": "photo", "label": "Photo of Respondent"},
            {"type": "geopoint", "name": "location", "label": "Location"},
            {"type": "date", "name": "next_visit", "label": "Next Visit Date"}
        ]
        
        # Create a DataFrame for display
        structure_df = pd.DataFrame(form_structure)
        
        # Display form structure
        st.dataframe(structure_df, use_container_width=True)
        
        # Download XForm button
        if st.button("Download XForm (XML)", key="download_xform_btn"):
            # In a real implementation, we would make an API call to get the XForm
            # For now, we'll use a simulated XForm
            xform = """<?xml version="1.0"?>
<h:html xmlns="http://www.w3.org/2002/xforms" xmlns:h="http://www.w3.org/1999/xhtml">
  <h:head>
    <h:title>Health Assessment Form</h:title>
    <model>
      <instance>
        <data id="health_assessment">
          <start/>
          <end/>
          <respondent_name/>
          <gender/>
          <age/>
          <education/>
          <health_issues/>
          <temperature/>
          <weight/>
          <height/>
          <bmi/>
          <bmi_note/>
          <photo/>
          <location/>
          <next_visit/>
        </data>
      </instance>
      <!-- Additional model elements would go here -->
    </model>
  </h:head>
  <h:body>
    <!-- Form elements would go here -->
  </h:body>
</h:html>"""
            
            # Create download link
            b64 = base64.b64encode(xform.encode()).decode()
            href = f'<a href="data:application/xml;base64,{b64}" download="health_assessment.xml">Download XForm</a>'
            st.markdown(href, unsafe_allow_html=True)
    
    with tab3:
        # Form preview
        st.markdown("#### Form Preview")
        st.info("This is a simplified preview of how the form would appear in ODK Collect.")
        
        # Create a simple form preview
        with st.form("form_preview"):
            st.text_input("Respondent Name")
            st.selectbox("Gender", ["", "Male", "Female", "Other"])
            st.number_input("Age", min_value=0, max_value=120)
            st.selectbox("Education Level", ["", "None", "Primary", "Secondary", "Tertiary"])
            st.multiselect("Health Issues", ["Hypertension", "Diabetes", "Asthma", "None"])
            st.number_input("Body Temperature (°C)", min_value=35.0, max_value=42.0, value=37.0, step=0.1)
            st.number_input("Weight (kg)", min_value=0.0, max_value=200.0, value=70.0, step=0.1)
            st.number_input("Height (cm)", min_value=0.0, max_value=250.0, value=170.0, step=0.1)
            st.file_uploader("Photo of Respondent", type=["jpg", "jpeg", "png"])
            st.date_input("Next Visit Date")
            
            st.form_submit_button("Submit (Preview Only)")
    
    with tab4:
        # Submissions
        st.markdown("#### Form Submissions")
        
        # Try to get submissions from the API
        success, submissions = utils.get_submissions(
            token=token,
            api_url=config.DATA_AGGREGATION_API,
            project_id=current_project.get('id'),
            form_id=current_form.get('id')
        )
        
        if not success:
            # If API call fails, use simulated data
            st.warning(f"Could not fetch submissions from API: {submissions}")
            st.info("Using simulated data for demonstration purposes.")
            
            # Simulated submissions data
            submissions = [
                {
                    "id": "sub1",
                    "form_id": current_form.get('id'),
                    "submitted_at": "2023-04-10T15:20:00Z",
                    "submitted_by": "collector1",
                    "data": {
                        "respondent_name": "John Doe",
                        "gender": "Male",
                        "age": 45,
                        "education": "Secondary",
                        "health_issues": "Hypertension",
                        "temperature": 37.2,
                        "weight": 78.5,
                        "height": 175,
                        "bmi": 25.6
                    }
                },
                {
                    "id": "sub2",
                    "form_id": current_form.get('id'),
                    "submitted_at": "2023-04-09T14:45:00Z",
                    "submitted_by": "collector2",
                    "data": {
                        "respondent_name": "Jane Smith",
                        "gender": "Female",
                        "age": 32,
                        "education": "Tertiary",
                        "health_issues": "None",
                        "temperature": 36.8,
                        "weight": 65.0,
                        "height": 168,
                        "bmi": 23.0
                    }
                },
                {
                    "id": "sub3",
                    "form_id": current_form.get('id'),
                    "submitted_at": "2023-04-08T11:30:00Z",
                    "submitted_by": "collector1",
                    "data": {
                        "respondent_name": "Robert Johnson",
                        "gender": "Male",
                        "age": 58,
                        "education": "Primary",
                        "health_issues": "Diabetes,Hypertension",
                        "temperature": 37.5,
                        "weight": 82.0,
                        "height": 180,
                        "bmi": 25.3
                    }
                }
            ]
        
        # Display submissions
        if not submissions:
            st.info("No submissions found for this form.")
        else:
            # Create a DataFrame for display
            # Extract submission metadata
            submissions_meta = [{
                "ID": sub.get("id"),
                "Submitted At": utils.format_timestamp(sub.get("submitted_at", "")),
                "Submitted By": sub.get("submitted_by", "Unknown")
            } for sub in submissions]
            
            submissions_meta_df = pd.DataFrame(submissions_meta)
            
            st.dataframe(submissions_meta_df, use_container_width=True)
            
            # Allow viewing individual submissions
            selected_submission = st.selectbox(
                "Select a submission to view details",
                options=[f"{sub.get('id')} - {utils.format_timestamp(sub.get('submitted_at', ''))}" for sub in submissions],
                index=0
            )
            
            if selected_submission:
                # Extract submission ID
                submission_id = selected_submission.split(" - ")[0]
                
                # Find the selected submission
                selected_sub = next((sub for sub in submissions if sub.get("id") == submission_id), None)
                
                if selected_sub:
                    st.markdown("##### Submission Details")
                    
                    # Display submission data
                    if "data" in selected_sub:
                        st.json(selected_sub["data"])
    
    # Back button
    if st.button("Back to Forms List", key="back_to_forms"):
        st.session_state.forms_action = "list"
        st.experimental_rerun()

