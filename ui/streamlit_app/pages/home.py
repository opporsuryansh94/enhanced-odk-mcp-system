"""
Home page for the ODK MCP System Streamlit UI.

This module renders the home page of the application, providing an overview
of the system and quick access to key features.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional

import config
import utils

def render():
    """Render the home page."""
    st.markdown('<h1 class="main-header">ODK MCP System</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Open Data Kit Implementation with Model Context Protocol</p>', unsafe_allow_html=True)
    
    # Welcome message
    user_info = st.session_state.user_info or {}
    user_name = user_info.get('name', st.session_state.username)
    
    st.markdown(f"### Welcome, {user_name}!")
    
    # System overview
    st.markdown("### System Overview")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="info-box">
            <h3>Projects</h3>
            <p>Create and manage data collection projects</p>
            <ul>
                <li>Organize forms by project</li>
                <li>Manage project settings</li>
                <li>Control access permissions</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="info-box">
            <h3>Forms</h3>
            <p>Design and deploy data collection forms</p>
            <ul>
                <li>Upload XLSForms</li>
                <li>Preview form structure</li>
                <li>Manage form versions</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="info-box">
            <h3>Data Collection</h3>
            <p>Collect and manage field data</p>
            <ul>
                <li>Submit data through forms</li>
                <li>View submission history</li>
                <li>Manage offline data sync</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="info-box">
            <h3>Data Analysis</h3>
            <p>Analyze collected data with powerful tools</p>
            <ul>
                <li>Descriptive statistics</li>
                <li>Inferential analysis</li>
                <li>Interactive data exploration</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="info-box">
            <h3>Reports</h3>
            <p>Generate comprehensive reports</p>
            <ul>
                <li>Create custom reports</li>
                <li>Export in multiple formats</li>
                <li>Share insights with stakeholders</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="info-box">
            <h3>Settings</h3>
            <p>Configure system settings</p>
            <ul>
                <li>Manage user accounts</li>
                <li>Configure API connections</li>
                <li>Set system preferences</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick actions
    st.markdown("### Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("Create Project", key="home_create_project"):
            st.session_state.page = "projects"
            st.session_state.projects_action = "create"
            st.experimental_rerun()
    
    with col2:
        if st.button("Upload Form", key="home_upload_form"):
            if st.session_state.current_project:
                st.session_state.page = "forms"
                st.session_state.forms_action = "upload"
                st.experimental_rerun()
            else:
                st.warning("Please select a project first")
    
    with col3:
        if st.button("Collect Data", key="home_collect_data"):
            if st.session_state.current_project:
                st.session_state.page = "data_collection"
                st.experimental_rerun()
            else:
                st.warning("Please select a project first")
    
    with col4:
        if st.button("Analyze Data", key="home_analyze_data"):
            if st.session_state.current_project:
                st.session_state.page = "data_analysis"
                st.experimental_rerun()
            else:
                st.warning("Please select a project first")
    
    # System status
    st.markdown("### System Status")
    
    # In a real implementation, we would make API calls to get actual system status
    # For now, we'll display simulated status information
    
    # Create sample data for demonstration
    status_data = {
        "Component": ["Form Management MCP", "Data Collection MCP", "Data Aggregation MCP", "Streamlit UI"],
        "Status": ["Online", "Online", "Online", "Online"],
        "Uptime": ["3d 12h 45m", "3d 12h 45m", "3d 12h 45m", "0h 15m"],
        "Load": [25, 15, 40, 10]
    }
    
    status_df = pd.DataFrame(status_data)
    
    # Display status table
    st.dataframe(status_df, use_container_width=True)
    
    # Display a sample chart
    st.markdown("### Recent Activity")
    
    # Create sample data for demonstration
    dates = pd.date_range(start="2023-01-01", periods=14, freq="D")
    submissions = [5, 8, 12, 15, 10, 7, 3, 6, 9, 14, 18, 12, 8, 10]
    
    activity_df = pd.DataFrame({
        "Date": dates,
        "Submissions": submissions
    })
    
    # Create a bar chart
    fig = px.bar(
        activity_df,
        x="Date",
        y="Submissions",
        title="Recent Form Submissions",
        labels={"Date": "Date", "Submissions": "Number of Submissions"},
        color_discrete_sequence=["#FF4B4B"]
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Documentation and resources
    st.markdown("### Documentation & Resources")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="info-box">
            <h3>ODK Documentation</h3>
            <p>Learn more about Open Data Kit:</p>
            <ul>
                <li><a href="https://docs.getodk.org/" target="_blank">ODK Documentation</a></li>
                <li><a href="https://forum.getodk.org/" target="_blank">ODK Forum</a></li>
                <li><a href="https://github.com/getodk" target="_blank">ODK GitHub</a></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="info-box">
            <h3>MCP System Documentation</h3>
            <p>Learn more about this implementation:</p>
            <ul>
                <li><a href="#" target="_blank">User Guide</a></li>
                <li><a href="#" target="_blank">API Documentation</a></li>
                <li><a href="#" target="_blank">GitHub Repository</a></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

