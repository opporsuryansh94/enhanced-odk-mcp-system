"""
Reports page for the ODK MCP System Streamlit UI.

This module renders the reports page of the application, allowing users to
generate, view, and download reports based on data analysis.
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
    """Render the reports page."""
    st.markdown('<h1 class="main-header">Reports</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Generate and view reports from your data</p>', unsafe_allow_html=True)
    
    # Check if a project is selected
    current_project = st.session_state.current_project
    if not current_project:
        st.warning("Please select a project first")
        if st.button("Go to Projects"):
            st.session_state.page = "projects"
            st.experimental_rerun()
        return
    
    # Initialize reports_action if not exists
    if "reports_action" not in st.session_state:
        st.session_state.reports_action = "list"
    
    # Handle different actions
    action = st.session_state.reports_action
    
    if action == "generate":
        render_generate_report()
    elif action == "view":
        render_view_report()
    else:  # Default to list
        render_list_reports()

def render_list_reports():
    """Render the list of reports."""
    # Get current project
    current_project = st.session_state.current_project
    
    st.markdown(f"### Reports for Project: {current_project.get('name', 'Unnamed Project')}")
    
    # Generate report button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Generate New Report", key="generate_report_btn"):
            st.session_state.reports_action = "generate"
            st.experimental_rerun()
    
    # In a real implementation, we would make an API call to get the list of reports
    # For now, we'll use simulated data
    
    # Check if we have a token
    token = st.session_state.token
    if not token:
        st.warning("Authentication token not found. Please sign in again.")
        return
    
    # Simulated reports data
    reports = [
        {
            "id": "report1",
            "title": "Health Assessment Summary Report",
            "form_id": "form1",
            "form_name": "Health Assessment Form",
            "created_at": "2023-04-15T14:30:00Z",
            "created_by": "analyst",
            "format": "pdf",
            "size": "1.2 MB",
            "analysis_type": "descriptive"
        },
        {
            "id": "report2",
            "title": "Household Survey Analysis",
            "form_id": "form2",
            "form_name": "Household Survey",
            "created_at": "2023-04-12T10:15:00Z",
            "created_by": "admin",
            "format": "html",
            "size": "850 KB",
            "analysis_type": "inferential"
        },
        {
            "id": "report3",
            "title": "Water Quality Test Results",
            "form_id": "form3",
            "form_name": "Water Quality Test",
            "created_at": "2023-04-10T16:45:00Z",
            "created_by": "collector4",
            "format": "pdf",
            "size": "1.5 MB",
            "analysis_type": "exploration"
        }
    ]
    
    # Display reports
    if not reports:
        st.info("No reports found for this project. Generate a new report to get started.")
    else:
        # Display reports in cards
        for report in reports:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                <div class="form-card">
                    <h3>{report.get('title', 'Unnamed Report')}</h3>
                    <p><small>Form: {report.get('form_name', 'Unknown Form')} | Type: {report.get('analysis_type', 'Unknown').title()}</small></p>
                    <p><small>Created: {utils.format_timestamp(report.get('created_at', ''))} | By: {report.get('created_by', 'Unknown')}</small></p>
                    <p><small>Format: {report.get('format', 'Unknown').upper()} | Size: {report.get('size', 'Unknown')}</small></p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # View report button
                if st.button("View", key=f"view_report_{report.get('id')}"):
                    st.session_state.current_report = report
                    st.session_state.reports_action = "view"
                    st.experimental_rerun()

def render_generate_report():
    """Render the generate report page."""
    # Get current project
    current_project = st.session_state.current_project
    
    st.markdown(f"### Generate Report for Project: {current_project.get('name', 'Unnamed Project')}")
    
    # Check if we have a token
    token = st.session_state.token
    if not token:
        st.warning("Authentication token not found. Please sign in again.")
        return
    
    # Check if we have analysis results from the data analysis page
    analysis_results = st.session_state.get("analysis_results_for_report")
    
    # Report configuration form
    with st.form("generate_report_form"):
        # Basic report information
        report_title = st.text_input("Report Title", value="Data Analysis Report")
        
        # Form selection
        # In a real implementation, we would fetch forms from the API
        forms = [
            {"id": "form1", "name": "Health Assessment Form"},
            {"id": "form2", "name": "Household Survey"},
            {"id": "form3", "name": "Water Quality Test"}
        ]
        
        form_options = [(f["id"], f["name"]) for f in forms]
        selected_form = st.selectbox(
            "Select Form",
            options=[f[0] for f in form_options],
            format_func=lambda x: next((f[1] for f in form_options if f[0] == x), x)
        )
        
        # Report format
        report_format = st.selectbox(
            "Report Format",
            options=["pdf", "html", "markdown"],
            format_func=lambda x: x.upper()
        )
        
        # Analysis types to include
        st.markdown("#### Analysis Types to Include")
        include_descriptive = st.checkbox("Descriptive Statistics", value=True)
        include_inferential = st.checkbox("Inferential Statistics", value=False)
        include_exploration = st.checkbox("Data Exploration", value=False)
        
        # Report sections
        st.markdown("#### Report Sections")
        include_executive_summary = st.checkbox("Executive Summary", value=True)
        include_methodology = st.checkbox("Methodology", value=True)
        include_findings = st.checkbox("Key Findings", value=True)
        include_recommendations = st.checkbox("Recommendations", value=True)
        include_appendix = st.checkbox("Appendix", value=False)
        
        # Custom sections
        custom_sections = st.text_area(
            "Custom Sections (one per line)",
            value="",
            help="Add custom section titles, one per line"
        )
        
        # Submit button
        submitted = st.form_submit_button("Generate Report")
        
        if submitted:
            # Prepare report configuration
            report_config = {
                "title": report_title,
                "form_id": selected_form,
                "format": report_format,
                "analysis_types": {
                    "descriptive": include_descriptive,
                    "inferential": include_inferential,
                    "exploration": include_exploration
                },
                "sections": {
                    "executive_summary": include_executive_summary,
                    "methodology": include_methodology,
                    "findings": include_findings,
                    "recommendations": include_recommendations,
                    "appendix": include_appendix
                },
                "custom_sections": [s.strip() for s in custom_sections.split("\n") if s.strip()]
            }
            
            # If we have analysis results, include them
            if analysis_results:
                report_config["analysis_results"] = analysis_results
            
            # Generate report
            with st.spinner("Generating report..."):
                success, response = utils.generate_report(
                    token=token,
                    api_url=config.DATA_AGGREGATION_API,
                    project_id=current_project.get('id'),
                    form_id=selected_form,
                    report_config=report_config
                )
            
            if success:
                st.success("Report generated successfully!")
                
                # Store report in session state
                st.session_state.current_report = {
                    "id": response.get("report_id", "report1"),
                    "title": report_title,
                    "form_id": selected_form,
                    "form_name": next((f[1] for f in form_options if f[0] == selected_form), "Unknown Form"),
                    "created_at": datetime.now().isoformat(),
                    "created_by": st.session_state.username,
                    "format": report_format,
                    "size": response.get("size", "1.2 MB"),
                    "analysis_type": ", ".join([k for k, v in report_config["analysis_types"].items() if v])
                }
                
                # Switch to view report
                st.session_state.reports_action = "view"
                st.experimental_rerun()
            else:
                st.error(f"Failed to generate report: {response}")
                st.info("Using simulated data for demonstration purposes.")
                
                # Simulate successful report generation for demo
                st.session_state.current_report = {
                    "id": "report1",
                    "title": report_title,
                    "form_id": selected_form,
                    "form_name": next((f[1] for f in form_options if f[0] == selected_form), "Unknown Form"),
                    "created_at": datetime.now().isoformat(),
                    "created_by": st.session_state.username,
                    "format": report_format,
                    "size": "1.2 MB",
                    "analysis_type": ", ".join([k for k, v in report_config["analysis_types"].items() if v])
                }
                
                # Switch to view report
                st.session_state.reports_action = "view"
                st.experimental_rerun()
    
    # Cancel button
    if st.button("Cancel", key="cancel_generate_report"):
        st.session_state.reports_action = "list"
        st.experimental_rerun()

def render_view_report():
    """Render the view report page."""
    # Get current report
    current_report = st.session_state.get("current_report")
    if not current_report:
        st.warning("No report selected")
        st.session_state.reports_action = "list"
        st.experimental_rerun()
        return
    
    st.markdown(f"### Report: {current_report.get('title', 'Unnamed Report')}")
    
    # Report metadata
    st.markdown(f"""
    **Form:** {current_report.get('form_name', 'Unknown Form')}  
    **Created:** {utils.format_timestamp(current_report.get('created_at', ''))}  
    **Created By:** {current_report.get('created_by', 'Unknown')}  
    **Format:** {current_report.get('format', 'Unknown').upper()}  
    **Size:** {current_report.get('size', 'Unknown')}  
    **Analysis Type:** {current_report.get('analysis_type', 'Unknown')}  
    """)
    
    # In a real implementation, we would fetch the report content from the API
    # For now, we'll use simulated data
    
    # Report preview
    st.markdown("#### Report Preview")
    
    # Simulated report content based on report format
    if current_report.get('format') == 'pdf':
        st.info("PDF preview not available in this demo. In a real implementation, the PDF would be embedded or available for download.")
        
        # Download button
        st.markdown(f"""
        <a href="#" download="{current_report.get('title', 'report')}.pdf" style="display: inline-block; padding: 0.5rem 1rem; background-color: #FF4B4B; color: white; text-decoration: none; border-radius: 4px;">
            Download PDF
        </a>
        """, unsafe_allow_html=True)
    
    elif current_report.get('format') == 'html':
        # Simulated HTML report content
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #FF4B4B;">{current_report.get('title', 'Unnamed Report')}</h1>
            <p><strong>Form:</strong> {current_report.get('form_name', 'Unknown Form')}</p>
            <p><strong>Generated:</strong> {utils.format_timestamp(current_report.get('created_at', ''))}</p>
            
            <h2>Executive Summary</h2>
            <p>This report provides an analysis of data collected using the {current_report.get('form_name', 'Unknown Form')}. The analysis includes descriptive statistics, key findings, and recommendations.</p>
            
            <h2>Methodology</h2>
            <p>Data was collected using the ODK MCP System and analyzed using various statistical methods. The analysis was performed on {current_report.get('analysis_type', 'Unknown')} data.</p>
            
            <h2>Key Findings</h2>
            <ul>
                <li>Finding 1: Lorem ipsum dolor sit amet, consectetur adipiscing elit.</li>
                <li>Finding 2: Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</li>
                <li>Finding 3: Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.</li>
            </ul>
            
            <h2>Recommendations</h2>
            <ol>
                <li>Recommendation 1: Lorem ipsum dolor sit amet, consectetur adipiscing elit.</li>
                <li>Recommendation 2: Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</li>
                <li>Recommendation 3: Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.</li>
            </ol>
            
            <div style="margin-top: 50px; border-top: 1px solid #ddd; padding-top: 10px; font-size: 0.8em; color: #777;">
                <p>Generated by ODK MCP System</p>
            </div>
        </div>
        """
        
        st.components.v1.html(html_content, height=600, scrolling=True)
        
        # Download button
        st.markdown(f"""
        <a href="#" download="{current_report.get('title', 'report')}.html" style="display: inline-block; padding: 0.5rem 1rem; background-color: #FF4B4B; color: white; text-decoration: none; border-radius: 4px;">
            Download HTML
        </a>
        """, unsafe_allow_html=True)
    
    elif current_report.get('format') == 'markdown':
        # Simulated Markdown report content
        markdown_content = f"""
        # {current_report.get('title', 'Unnamed Report')}
        
        **Form:** {current_report.get('form_name', 'Unknown Form')}  
        **Generated:** {utils.format_timestamp(current_report.get('created_at', ''))}
        
        ## Executive Summary
        
        This report provides an analysis of data collected using the {current_report.get('form_name', 'Unknown Form')}. The analysis includes descriptive statistics, key findings, and recommendations.
        
        ## Methodology
        
        Data was collected using the ODK MCP System and analyzed using various statistical methods. The analysis was performed on {current_report.get('analysis_type', 'Unknown')} data.
        
        ## Key Findings
        
        1. Finding 1: Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        2. Finding 2: Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
        3. Finding 3: Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
        
        ## Recommendations
        
        1. Recommendation 1: Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        2. Recommendation 2: Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
        3. Recommendation 3: Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
        
        ---
        
        Generated by ODK MCP System
        """
        
        st.markdown(markdown_content)
        
        # Download button
        st.markdown(f"""
        <a href="#" download="{current_report.get('title', 'report')}.md" style="display: inline-block; padding: 0.5rem 1rem; background-color: #FF4B4B; color: white; text-decoration: none; border-radius: 4px;">
            Download Markdown
        </a>
        """, unsafe_allow_html=True)
    
    # Share options
    st.markdown("#### Share Report")
    
    col1, col2 = st.columns(2)
    
    with col1:
        email = st.text_input("Email Address")
        if st.button("Email Report", key="email_report"):
            if email:
                st.success(f"Report sent to {email}")
            else:
                st.error("Please enter an email address")
    
    with col2:
        if st.button("Copy Link", key="copy_link"):
            st.success("Report link copied to clipboard")
    
    # Back button
    if st.button("Back to Reports List", key="back_to_reports"):
        st.session_state.reports_action = "list"
        st.experimental_rerun()

