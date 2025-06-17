"""
Data Collection page for the ODK MCP System Streamlit UI.

This module renders the data collection page of the application, allowing users to
collect data using forms and manage submissions.
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
    """Render the data collection page."""
    st.markdown('<h1 class="main-header">Data Collection</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Collect and manage form data</p>', unsafe_allow_html=True)
    
    # Check if a project is selected
    current_project = st.session_state.current_project
    if not current_project:
        st.warning("Please select a project first")
        if st.button("Go to Projects"):
            st.session_state.page = "projects"
            st.experimental_rerun()
        return
    
    # Initialize data_collection_action if not exists
    if "data_collection_action" not in st.session_state:
        st.session_state.data_collection_action = "select_form"
    
    # Handle different actions
    action = st.session_state.data_collection_action
    
    if action == "collect":
        render_collect_data()
    elif action == "view_submissions":
        render_view_submissions()
    else:  # Default to select_form
        render_select_form()

def render_select_form():
    """Render the form selection page."""
    # Get current project
    current_project = st.session_state.current_project
    
    st.markdown(f"### Select a Form for Data Collection in Project: {current_project.get('name', 'Unnamed Project')}")
    
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
        if st.button("Go to Forms"):
            st.session_state.page = "forms"
            st.experimental_rerun()
        return
    
    # Display forms in cards
    for form in forms:
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"""
            <div class="form-card">
                <h3>{form.get('name', 'Unnamed Form')}</h3>
                <p><small>Version: {form.get('version', '1.0')} | Created: {utils.format_timestamp(form.get('created_at', ''))}</small></p>
                <p><small>Submissions: {form.get('submission_count', 0)}</small></p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Collect data button
            if st.button("Collect Data", key=f"collect_data_{form.get('id')}"):
                utils.set_current_form(
                    form_id=form.get('id'),
                    form_name=form.get('name')
                )
                st.session_state.data_collection_action = "collect"
                st.experimental_rerun()
        
        with col3:
            # View submissions button
            if st.button("View Submissions", key=f"view_submissions_{form.get('id')}"):
                utils.set_current_form(
                    form_id=form.get('id'),
                    form_name=form.get('name')
                )
                st.session_state.data_collection_action = "view_submissions"
                st.experimental_rerun()

def render_collect_data():
    """Render the data collection page."""
    # Get current project and form
    current_project = st.session_state.current_project
    current_form = st.session_state.current_form
    
    if not current_form:
        st.warning("No form selected")
        st.session_state.data_collection_action = "select_form"
        st.experimental_rerun()
        return
    
    st.markdown(f"### Collect Data: {current_form.get('name', 'Unnamed Form')}")
    
    # In a real implementation, we would make an API call to get the form structure
    # For now, we'll use simulated data
    
    # Check if we have a token
    token = st.session_state.token
    if not token:
        st.warning("Authentication token not found. Please sign in again.")
        return
    
    # Simulated form structure for Health Assessment Form
    if current_form.get('id') == "form1" or current_form.get('name') == "Health Assessment Form":
        with st.form("data_collection_form"):
            st.text_input("Respondent Name", key="respondent_name")
            st.selectbox("Gender", ["", "Male", "Female", "Other"], key="gender")
            st.number_input("Age", min_value=0, max_value=120, key="age")
            st.selectbox("Education Level", ["", "None", "Primary", "Secondary", "Tertiary"], key="education")
            st.multiselect("Health Issues", ["Hypertension", "Diabetes", "Asthma", "None"], key="health_issues")
            st.number_input("Body Temperature (°C)", min_value=35.0, max_value=42.0, value=37.0, step=0.1, key="temperature")
            st.number_input("Weight (kg)", min_value=0.0, max_value=200.0, value=70.0, step=0.1, key="weight")
            st.number_input("Height (cm)", min_value=0.0, max_value=250.0, value=170.0, step=0.1, key="height")
            st.file_uploader("Photo of Respondent", type=["jpg", "jpeg", "png"], key="photo")
            st.date_input("Next Visit Date", key="next_visit")
            
            submitted = st.form_submit_button("Submit Data")
            
            if submitted:
                # In a real implementation, we would make an API call to submit the data
                # For now, we'll simulate a successful submission
                
                # Get form data
                form_data = {
                    "respondent_name": st.session_state.respondent_name,
                    "gender": st.session_state.gender,
                    "age": st.session_state.age,
                    "education": st.session_state.education,
                    "health_issues": ",".join(st.session_state.health_issues),
                    "temperature": st.session_state.temperature,
                    "weight": st.session_state.weight,
                    "height": st.session_state.height,
                    "next_visit": str(st.session_state.next_visit)
                }
                
                # Calculate BMI
                if st.session_state.weight > 0 and st.session_state.height > 0:
                    bmi = st.session_state.weight / ((st.session_state.height / 100) ** 2)
                    form_data["bmi"] = round(bmi, 1)
                
                # Display success message
                st.success("Data submitted successfully!")
                
                # Display submitted data
                st.json(form_data)
                
                # Option to collect more data or view submissions
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Collect More Data", key="collect_more_data"):
                        st.experimental_rerun()
                
                with col2:
                    if st.button("View Submissions", key="view_submissions_after_collect"):
                        st.session_state.data_collection_action = "view_submissions"
                        st.experimental_rerun()
    
    # Simulated form structure for Household Survey
    elif current_form.get('id') == "form2" or current_form.get('name') == "Household Survey":
        with st.form("data_collection_form"):
            st.text_input("Household ID", key="household_id")
            st.text_input("Respondent Name", key="respondent_name")
            st.selectbox("Relationship to Head", ["", "Head", "Spouse", "Child", "Other Relative", "Non-Relative"], key="relationship")
            st.number_input("Household Size", min_value=1, max_value=50, value=4, key="household_size")
            st.selectbox("Dwelling Type", ["", "Permanent", "Semi-Permanent", "Temporary"], key="dwelling_type")
            st.number_input("Number of Rooms", min_value=1, max_value=20, value=2, key="rooms")
            st.multiselect("Water Sources", ["Piped Water", "Borehole", "Well", "Spring", "River/Stream", "Rainwater", "Bottled Water"], key="water_sources")
            st.selectbox("Main Source of Lighting", ["", "Electricity", "Solar", "Generator", "Kerosene", "Candles", "None"], key="lighting")
            st.selectbox("Main Cooking Fuel", ["", "Electricity", "Gas", "Kerosene", "Charcoal", "Firewood", "Dung", "None"], key="cooking_fuel")
            st.multiselect("Assets Owned", ["Radio", "Television", "Mobile Phone", "Computer", "Refrigerator", "Bicycle", "Motorcycle", "Car"], key="assets")
            st.number_input("Monthly Income (USD)", min_value=0, value=200, key="income")
            
            submitted = st.form_submit_button("Submit Data")
            
            if submitted:
                # In a real implementation, we would make an API call to submit the data
                # For now, we'll simulate a successful submission
                
                # Get form data
                form_data = {
                    "household_id": st.session_state.household_id,
                    "respondent_name": st.session_state.respondent_name,
                    "relationship": st.session_state.relationship,
                    "household_size": st.session_state.household_size,
                    "dwelling_type": st.session_state.dwelling_type,
                    "rooms": st.session_state.rooms,
                    "water_sources": ",".join(st.session_state.water_sources),
                    "lighting": st.session_state.lighting,
                    "cooking_fuel": st.session_state.cooking_fuel,
                    "assets": ",".join(st.session_state.assets),
                    "income": st.session_state.income
                }
                
                # Display success message
                st.success("Data submitted successfully!")
                
                # Display submitted data
                st.json(form_data)
                
                # Option to collect more data or view submissions
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Collect More Data", key="collect_more_data"):
                        st.experimental_rerun()
                
                with col2:
                    if st.button("View Submissions", key="view_submissions_after_collect"):
                        st.session_state.data_collection_action = "view_submissions"
                        st.experimental_rerun()
    
    # Simulated form structure for Water Quality Test
    elif current_form.get('id') == "form3" or current_form.get('name') == "Water Quality Test":
        with st.form("data_collection_form"):
            st.text_input("Sample ID", key="sample_id")
            st.text_input("Location Name", key="location_name")
            st.selectbox("Water Source Type", ["", "Tap Water", "Borehole", "Well", "Spring", "River/Stream", "Lake/Pond", "Rainwater"], key="source_type")
            st.date_input("Sample Date", key="sample_date")
            st.time_input("Sample Time", key="sample_time")
            st.number_input("Temperature (°C)", min_value=0.0, max_value=50.0, value=25.0, step=0.1, key="temperature")
            st.number_input("pH", min_value=0.0, max_value=14.0, value=7.0, step=0.1, key="ph")
            st.number_input("Turbidity (NTU)", min_value=0.0, max_value=1000.0, value=5.0, step=0.1, key="turbidity")
            st.number_input("Dissolved Oxygen (mg/L)", min_value=0.0, max_value=20.0, value=8.0, step=0.1, key="dissolved_oxygen")
            st.number_input("Conductivity (µS/cm)", min_value=0.0, max_value=5000.0, value=500.0, step=1.0, key="conductivity")
            st.number_input("Total Dissolved Solids (mg/L)", min_value=0.0, max_value=5000.0, value=250.0, step=1.0, key="tds")
            st.selectbox("E. coli Presence", ["", "Present", "Absent"], key="ecoli")
            st.selectbox("Coliform Presence", ["", "Present", "Absent"], key="coliform")
            st.text_area("Notes", key="notes")
            
            submitted = st.form_submit_button("Submit Data")
            
            if submitted:
                # In a real implementation, we would make an API call to submit the data
                # For now, we'll simulate a successful submission
                
                # Get form data
                form_data = {
                    "sample_id": st.session_state.sample_id,
                    "location_name": st.session_state.location_name,
                    "source_type": st.session_state.source_type,
                    "sample_date": str(st.session_state.sample_date),
                    "sample_time": str(st.session_state.sample_time),
                    "temperature": st.session_state.temperature,
                    "ph": st.session_state.ph,
                    "turbidity": st.session_state.turbidity,
                    "dissolved_oxygen": st.session_state.dissolved_oxygen,
                    "conductivity": st.session_state.conductivity,
                    "tds": st.session_state.tds,
                    "ecoli": st.session_state.ecoli,
                    "coliform": st.session_state.coliform,
                    "notes": st.session_state.notes
                }
                
                # Display success message
                st.success("Data submitted successfully!")
                
                # Display submitted data
                st.json(form_data)
                
                # Option to collect more data or view submissions
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Collect More Data", key="collect_more_data"):
                        st.experimental_rerun()
                
                with col2:
                    if st.button("View Submissions", key="view_submissions_after_collect"):
                        st.session_state.data_collection_action = "view_submissions"
                        st.experimental_rerun()
    
    # Generic form for other forms
    else:
        st.info("This is a placeholder for the selected form. In a real implementation, the form would be dynamically generated based on the form definition.")
        
        with st.form("data_collection_form"):
            st.text_input("Field 1", key="field1")
            st.text_input("Field 2", key="field2")
            st.number_input("Field 3", key="field3")
            st.selectbox("Field 4", ["Option 1", "Option 2", "Option 3"], key="field4")
            
            submitted = st.form_submit_button("Submit Data")
            
            if submitted:
                # Display success message
                st.success("Data submitted successfully!")
                
                # Display submitted data
                form_data = {
                    "field1": st.session_state.field1,
                    "field2": st.session_state.field2,
                    "field3": st.session_state.field3,
                    "field4": st.session_state.field4
                }
                
                st.json(form_data)
    
    # Back button
    if st.button("Back to Form Selection", key="back_to_form_selection"):
        st.session_state.data_collection_action = "select_form"
        st.experimental_rerun()

def render_view_submissions():
    """Render the view submissions page."""
    # Get current project and form
    current_project = st.session_state.current_project
    current_form = st.session_state.current_form
    
    if not current_form:
        st.warning("No form selected")
        st.session_state.data_collection_action = "select_form"
        st.experimental_rerun()
        return
    
    st.markdown(f"### Submissions for Form: {current_form.get('name', 'Unnamed Form')}")
    
    # In a real implementation, we would make an API call to get the submissions
    # For now, we'll use simulated data
    
    # Check if we have a token
    token = st.session_state.token
    if not token:
        st.warning("Authentication token not found. Please sign in again.")
        return
    
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
        
        # Simulated submissions data based on form type
        if current_form.get('id') == "form1" or current_form.get('name') == "Health Assessment Form":
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
                        "bmi": 25.6,
                        "next_visit": "2023-05-10"
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
                        "bmi": 23.0,
                        "next_visit": "2023-05-15"
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
                        "bmi": 25.3,
                        "next_visit": "2023-04-22"
                    }
                }
            ]
        elif current_form.get('id') == "form2" or current_form.get('name') == "Household Survey":
            submissions = [
                {
                    "id": "sub4",
                    "form_id": current_form.get('id'),
                    "submitted_at": "2023-04-10T13:10:00Z",
                    "submitted_by": "collector3",
                    "data": {
                        "household_id": "HH001",
                        "respondent_name": "Michael Brown",
                        "relationship": "Head",
                        "household_size": 5,
                        "dwelling_type": "Permanent",
                        "rooms": 3,
                        "water_sources": "Piped Water,Rainwater",
                        "lighting": "Electricity",
                        "cooking_fuel": "Gas",
                        "assets": "Radio,Television,Mobile Phone",
                        "income": 350
                    }
                },
                {
                    "id": "sub5",
                    "form_id": current_form.get('id'),
                    "submitted_at": "2023-04-09T10:25:00Z",
                    "submitted_by": "collector2",
                    "data": {
                        "household_id": "HH002",
                        "respondent_name": "Sarah Wilson",
                        "relationship": "Spouse",
                        "household_size": 3,
                        "dwelling_type": "Semi-Permanent",
                        "rooms": 2,
                        "water_sources": "Borehole",
                        "lighting": "Solar",
                        "cooking_fuel": "Charcoal",
                        "assets": "Radio,Mobile Phone",
                        "income": 180
                    }
                }
            ]
        elif current_form.get('id') == "form3" or current_form.get('name') == "Water Quality Test":
            submissions = [
                {
                    "id": "sub6",
                    "form_id": current_form.get('id'),
                    "submitted_at": "2023-04-10T09:45:00Z",
                    "submitted_by": "collector4",
                    "data": {
                        "sample_id": "WS001",
                        "location_name": "Community Well 1",
                        "source_type": "Well",
                        "sample_date": "2023-04-10",
                        "sample_time": "09:30:00",
                        "temperature": 24.5,
                        "ph": 7.2,
                        "turbidity": 4.8,
                        "dissolved_oxygen": 7.8,
                        "conductivity": 520,
                        "tds": 260,
                        "ecoli": "Absent",
                        "coliform": "Present",
                        "notes": "Water appears clear but has slight odor."
                    }
                },
                {
                    "id": "sub7",
                    "form_id": current_form.get('id'),
                    "submitted_at": "2023-04-09T14:20:00Z",
                    "submitted_by": "collector4",
                    "data": {
                        "sample_id": "WS002",
                        "location_name": "River Crossing",
                        "source_type": "River/Stream",
                        "sample_date": "2023-04-09",
                        "sample_time": "14:00:00",
                        "temperature": 26.8,
                        "ph": 6.8,
                        "turbidity": 12.5,
                        "dissolved_oxygen": 6.2,
                        "conductivity": 380,
                        "tds": 190,
                        "ecoli": "Present",
                        "coliform": "Present",
                        "notes": "Water is turbid with visible suspended particles."
                    }
                }
            ]
        else:
            submissions = []
    
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
                    # Create tabs for different views
                    tab1, tab2 = st.tabs(["Formatted View", "Raw JSON"])
                    
                    with tab1:
                        # Display data in a more user-friendly format
                        for key, value in selected_sub["data"].items():
                            st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
                    
                    with tab2:
                        # Display raw JSON
                        st.json(selected_sub["data"])
        
        # Export options
        st.markdown("##### Export Submissions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Export as CSV", key="export_csv"):
                # Create a DataFrame from all submissions data
                all_data = []
                for sub in submissions:
                    if "data" in sub:
                        row = sub["data"].copy()
                        row["submission_id"] = sub.get("id")
                        row["submitted_at"] = utils.format_timestamp(sub.get("submitted_at", ""))
                        row["submitted_by"] = sub.get("submitted_by", "Unknown")
                        all_data.append(row)
                
                if all_data:
                    df = pd.DataFrame(all_data)
                    
                    # Convert DataFrame to CSV
                    csv = df.to_csv(index=False)
                    
                    # Create download link
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="{current_form.get("name", "form")}_submissions.csv">Download CSV</a>'
                    st.markdown(href, unsafe_allow_html=True)
        
        with col2:
            if st.button("Export as JSON", key="export_json"):
                # Create a JSON object with all submissions
                export_data = {
                    "form_id": current_form.get("id"),
                    "form_name": current_form.get("name"),
                    "export_date": datetime.now().isoformat(),
                    "submissions": submissions
                }
                
                # Convert to JSON string
                json_str = json.dumps(export_data, indent=2)
                
                # Create download link
                b64 = base64.b64encode(json_str.encode()).decode()
                href = f'<a href="data:file/json;base64,{b64}" download="{current_form.get("name", "form")}_submissions.json">Download JSON</a>'
                st.markdown(href, unsafe_allow_html=True)
    
    # Buttons for navigation
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Back to Form Selection", key="back_to_form_selection_from_submissions"):
            st.session_state.data_collection_action = "select_form"
            st.experimental_rerun()
    
    with col2:
        if st.button("Collect More Data", key="collect_more_data_from_submissions"):
            st.session_state.data_collection_action = "collect"
            st.experimental_rerun()

