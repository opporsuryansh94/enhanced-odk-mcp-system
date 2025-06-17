"""
Data Analysis page for the ODK MCP System Streamlit UI.

This module renders the data analysis page of the application, allowing users to
perform various analyses on collected data.
"""

import streamlit as st
import pandas as pd
import json
import io
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

import config
import utils

def render():
    """Render the data analysis page."""
    st.markdown("<h1 class=\"main-header\">Data Analysis</h1>", unsafe_allow_html=True)
    st.markdown("<p class=\"sub-header\">Analyze collected data and generate insights</p>", unsafe_allow_html=True)
    
    # Check if a project is selected
    current_project = st.session_state.current_project
    if not current_project:
        st.warning("Please select a project first")
        if st.button("Go to Projects"):
            st.session_state.page = "projects"
            st.experimental_rerun()
        return
    
    # Initialize data_analysis_action if not exists
    if "data_analysis_action" not in st.session_state:
        st.session_state.data_analysis_action = "select_form"
    
    # Handle different actions
    action = st.session_state.data_analysis_action
    
    if action == "analyze":
        render_analyze_data()
    else:  # Default to select_form
        render_select_form_for_analysis()

def render_select_form_for_analysis():
    """Render the form selection page for analysis."""
    # Get current project
    current_project = st.session_state.current_project
    
    st.markdown(f"### Select a Form for Analysis in Project: {current_project.get(\'name\', \'Unnamed Project\')}")
    
    # Check if we have a token
    token = st.session_state.token
    if not token:
        st.warning("Authentication token not found. Please sign in again.")
        return
    
    # Try to get forms from the API
    success, forms = utils.get_forms(token, config.FORM_MANAGEMENT_API, current_project.get(\'id\'))
    
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
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"""
            <div class="form-card">
                <h3>{form.get(\'name\', \'Unnamed Form\')}</h3>
                <p><small>Version: {form.get(\'version\', \'1.0\')} | Created: {utils.format_timestamp(form.get(\'created_at\', \'\'))}</small></p>
                <p><small>Submissions: {form.get(\'submission_count\', 0)}</small></p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Analyze data button
            if st.button("Analyze Data", key=f"analyze_data_{form.get(\'id\')}"):
                utils.set_current_form(
                    form_id=form.get(\'id\'),
                    form_name=form.get(\'name\')
                )
                st.session_state.data_analysis_action = "analyze"
                st.experimental_rerun()

def render_analyze_data():
    """Render the data analysis page."""
    # Get current project and form
    current_project = st.session_state.current_project
    current_form = st.session_state.current_form
    
    if not current_form:
        st.warning("No form selected")
        st.session_state.data_analysis_action = "select_form"
        st.experimental_rerun()
        return
    
    st.markdown(f"### Analyze Data: {current_form.get(\'name\', \'Unnamed Form\')}")
    
    # Check if we have a token
    token = st.session_state.token
    if not token:
        st.warning("Authentication token not found. Please sign in again.")
        return
    
    # Analysis options
    analysis_type = st.selectbox(
        "Select Analysis Type",
        ["Descriptive Statistics", "Inferential Statistics", "Data Exploration"]
    )
    
    # Configuration for each analysis type
    if analysis_type == "Descriptive Statistics":
        render_descriptive_analysis_config()
    elif analysis_type == "Inferential Statistics":
        render_inferential_analysis_config()
    elif analysis_type == "Data Exploration":
        render_exploration_analysis_config()
    
    # Back button
    if st.button("Back to Form Selection", key="back_to_form_selection_analysis"):
        st.session_state.data_analysis_action = "select_form"
        st.experimental_rerun()

def render_descriptive_analysis_config():
    """Render configuration options for descriptive analysis."""
    st.markdown("#### Descriptive Statistics Configuration")
    
    # In a real implementation, we would fetch form variables for selection
    # For now, we use a generic approach
    
    # Options for analysis
    include_summary_stats = st.checkbox("Include Summary Statistics", value=True)
    include_frequency_tables = st.checkbox("Include Frequency Tables", value=True)
    include_visualizations = st.checkbox("Include Visualizations", value=True)
    
    # Visualization options
    if include_visualizations:
        st.markdown("##### Visualization Options")
        
        # Simulated variables for selection
        variables = ["age", "gender", "education", "income", "health_score"]
        
        selected_variables = st.multiselect(
            "Select variables for visualization",
            options=variables,
            default=variables[:2]
        )
        
        plot_types = st.multiselect(
            "Select plot types",
            options=["Histogram", "Box Plot", "Bar Chart", "Pie Chart", "Scatter Plot"],
            default=["Histogram", "Bar Chart"]
        )
    
    # Run analysis button
    if st.button("Run Descriptive Analysis", key="run_descriptive_analysis"):
        # Prepare analysis configuration
        analysis_config = {
            "include_summary_stats": include_summary_stats,
            "include_frequency_tables": include_frequency_tables,
            "include_visualizations": include_visualizations,
            "visualization_options": {
                "variables": selected_variables if include_visualizations else [],
                "plot_types": plot_types if include_visualizations else []
            }
        }
        
        # Run analysis
        run_analysis("descriptive", analysis_config)

def render_inferential_analysis_config():
    """Render configuration options for inferential analysis."""
    st.markdown("#### Inferential Statistics Configuration")
    
    # In a real implementation, we would fetch form variables for selection
    # For now, we use a generic approach
    
    # Simulated variables for selection
    numeric_variables = ["age", "income", "health_score", "test_score"]
    categorical_variables = ["gender", "education", "region", "treatment_group"]
    
    # Select test type
    test_type = st.selectbox(
        "Select Test Type",
        ["T-Test", "ANOVA", "Chi-Square Test", "Correlation", "Regression"]
    )
    
    # Configuration for each test type
    if test_type == "T-Test":
        st.markdown("##### T-Test Configuration")
        t_test_subtype = st.selectbox("Select T-Test Subtype", ["One-Sample", "Two-Sample Independent"])
        
        if t_test_subtype == "One-Sample":
            variable = st.selectbox("Select Variable", numeric_variables)
            population_mean = st.number_input("Population Mean (H0)", value=0.0)
            analysis_config = {"test_type": "t_test", "subtype": "one_sample", "variable": variable, "population_mean": population_mean}
        
        elif t_test_subtype == "Two-Sample Independent":
            variable = st.selectbox("Select Dependent Variable", numeric_variables)
            group_variable = st.selectbox("Select Grouping Variable", categorical_variables)
            analysis_config = {"test_type": "t_test", "subtype": "two_sample", "variable": variable, "group_variable": group_variable}
    
    elif test_type == "ANOVA":
        st.markdown("##### ANOVA Configuration")
        variable = st.selectbox("Select Dependent Variable", numeric_variables)
        group_variable = st.selectbox("Select Grouping Variable", categorical_variables)
        analysis_config = {"test_type": "anova", "variable": variable, "group_variable": group_variable}
    
    elif test_type == "Chi-Square Test":
        st.markdown("##### Chi-Square Test Configuration")
        variable1 = st.selectbox("Select Variable 1", categorical_variables)
        variable2 = st.selectbox("Select Variable 2", categorical_variables)
        analysis_config = {"test_type": "chi_square", "variable1": variable1, "variable2": variable2}
    
    elif test_type == "Correlation":
        st.markdown("##### Correlation Configuration")
        selected_variables = st.multiselect("Select Variables (Numeric)", numeric_variables, default=numeric_variables[:2])
        correlation_method = st.selectbox("Select Correlation Method", ["Pearson", "Spearman", "Kendall"])
        analysis_config = {"test_type": "correlation", "variables": selected_variables, "method": correlation_method.lower()}
    
    elif test_type == "Regression":
        st.markdown("##### Regression Configuration")
        regression_type = st.selectbox("Select Regression Type", ["Linear Regression", "Logistic Regression"])
        dependent_variable = st.selectbox("Select Dependent Variable", numeric_variables if regression_type == "Linear Regression" else categorical_variables)
        independent_variables = st.multiselect("Select Independent Variables", numeric_variables + categorical_variables, default=numeric_variables[:1] + categorical_variables[:1])
        analysis_config = {"test_type": "regression", "subtype": regression_type.lower().replace(" ", "_"), "dependent_variable": dependent_variable, "independent_variables": independent_variables}
    
    # Run analysis button
    if st.button("Run Inferential Analysis", key="run_inferential_analysis"):
        # Run analysis
        run_analysis("inferential", analysis_config)

def render_exploration_analysis_config():
    """Render configuration options for data exploration."""
    st.markdown("#### Data Exploration Configuration")
    
    # In a real implementation, we would fetch form variables for selection
    # For now, we use a generic approach
    
    # Simulated variables for selection
    all_variables = ["age", "gender", "education", "income", "health_score", "region", "treatment_group"]
    
    # Filter options
    st.markdown("##### Filter Data")
    filter_variable = st.selectbox("Select variable to filter", ["None"] + all_variables, key="filter_var")
    
    if filter_variable != "None":
        filter_operator = st.selectbox(
            "Select operator",
            ["==", "!=", ">", ">=", "<", "<=", "in", "not in", "contains"],
            key="filter_op"
        )
        filter_value = st.text_input("Enter filter value (for \'in\' or \'not in\', use comma-separated values)", key="filter_val")
    
    # Group by options
    st.markdown("##### Group Data")
    group_variables = st.multiselect("Select variables to group by", all_variables, key="group_vars")
    
    if group_variables:
        agg_variable = st.selectbox("Select variable to aggregate", all_variables, key="agg_var")
        agg_function = st.selectbox(
            "Select aggregation function",
            ["mean", "sum", "count", "min", "max", "median", "std"],
            key="agg_func"
        )
    
    # Plot options
    st.markdown("##### Plot Data")
    plot_type = st.selectbox(
        "Select plot type",
        ["Bar Chart", "Line Chart", "Scatter Plot", "Box Plot", "Histogram"],
        key="plot_type"
    )
    
    x_variable = st.selectbox("Select X-axis variable", ["None"] + all_variables, key="x_var")
    y_variable = st.selectbox("Select Y-axis variable", ["None"] + all_variables, key="y_var")
    hue_variable = st.selectbox("Select Hue variable (for color grouping)", ["None"] + all_variables, key="hue_var")
    
    # Run analysis button
    if st.button("Explore Data", key="run_exploration_analysis"):
        # Prepare analysis configuration
        analysis_config = {"filters": [], "group_by": None, "plot": None}
        
        if filter_variable != "None" and filter_value:
            analysis_config["filters"].append({
                "column": filter_variable,
                "operator": filter_operator,
                "value": filter_value.split(",") if filter_operator in ["in", "not in"] else filter_value
            })
        
        if group_variables and agg_variable and agg_function:
            analysis_config["group_by"] = {
                "columns": group_variables,
                "aggregations": {agg_variable: [agg_function]}
            }
        
        if plot_type and x_variable != "None":
            analysis_config["plot"] = {
                "type": plot_type.lower().replace(" ", "_"),
                "x": x_variable,
                "y": y_variable if y_variable != "None" else None,
                "hue": hue_variable if hue_variable != "None" else None
            }
        
        # Run analysis
        run_analysis("exploration", analysis_config)

def run_analysis(analysis_type: str, analysis_config: Dict):
    """Run the specified analysis and display results."""
    # Get current project and form
    current_project = st.session_state.current_project
    current_form = st.session_state.current_form
    token = st.session_state.token
    
    st.markdown(f"### Running {analysis_type.replace(\'_\', \' \').title()} Analysis...")
    
    # In a real implementation, we would make an API call to run the analysis
    # For now, we use simulated results
    
    with st.spinner("Analyzing data..."):
        success, results = utils.run_data_analysis(
            token=token,
            api_url=config.DATA_AGGREGATION_API,
            project_id=current_project.get(\'id\'),
            form_id=current_form.get(\'id\'),
            analysis_type=analysis_type,
            analysis_config=analysis_config
        )
    
    if not success:
        # If API call fails, use simulated data
        st.warning(f"Could not run analysis via API: {results}")
        st.info("Using simulated data for demonstration purposes.")
        
        # Simulated results based on analysis type
        if analysis_type == "descriptive":
            results = {
                "status": "success",
                "data_shape": {"rows": 120, "columns": 15},
                "summary_statistics": {
                    "age": {"count": 120, "mean": 35.5, "std": 12.2, "min": 18, "q1": 25, "median": 34, "q3": 45, "max": 72},
                    "income": {"count": 110, "mean": 550.0, "std": 250.0, "min": 100, "q1": 350, "median": 500, "q3": 700, "max": 1500}
                },
                "frequency_tables": {
                    "gender": {"Male": 65, "Female": 55},
                    "education": {"Primary": 30, "Secondary": 50, "Tertiary": 35, "None": 5}
                },
                "visualizations": [
                    {"type": "histogram", "column": "age", "title": "Age Distribution", "image_base64": "..."},
                    {"type": "bar_chart", "column": "gender", "title": "Gender Distribution", "image_base64": "..."}
                ]
            }
        elif analysis_type == "inferential":
            results = {
                "status": "success",
                "analyses": [
                    {
                        "type": "t_test",
                        "subtype": "two_sample",
                        "variable": "income",
                        "group_variable": "gender",
                        "result": {"statistic": 2.5, "p_value": 0.015, "significant": True},
                        "visualization": {"type": "box_plot", "title": "Income by Gender", "image_base64": "..."}
                    },
                    {
                        "type": "correlation",
                        "variables": ["age", "income"],
                        "method": "pearson",
                        "result": {"correlation_matrix": [[1.0, 0.45], [0.45, 1.0]], "p_values": [[0.0, 0.001], [0.001, 0.0]]},
                        "visualization": {"type": "heatmap", "title": "Correlation Matrix (Age, Income)", "image_base64": "..."}
                    }
                ]
            }
        elif analysis_type == "exploration":
            results = {
                "status": "success",
                "original_data_shape": {"rows": 120, "columns": 15},
                "filtered_data_shape": {"rows": 80, "columns": 15},
                "grouped_data_shape": {"rows": 2, "columns": 3},
                "plot": {
                    "type": "bar_chart",
                    "x": "gender",
                    "y": "income_mean",
                    "title": "Average Income by Gender (Filtered)",
                    "image_base64": "..."
                },
                "data_preview": {
                    "total_rows": 2,
                    "total_columns": 3,
                    "preview_rows": 2,
                    "columns": [
                        {"name": "gender", "dtype": "object"},
                        {"name": "income_mean", "dtype": "float64"},
                        {"name": "income_count", "dtype": "int64"}
                    ],
                    "preview_data": [
                        {"gender": "Male", "income_mean": 620.0, "income_count": 45},
                        {"gender": "Female", "income_mean": 480.0, "income_count": 35}
                    ]
                }
            }
        else:
            results = {"status": "error", "message": "Unknown analysis type"}
    
    # Display results
    if results.get("status") == "success":
        st.success("Analysis completed successfully!")
        
        # Display results based on analysis type
        if analysis_type == "descriptive":
            display_descriptive_results(results)
        elif analysis_type == "inferential":
            display_inferential_results(results)
        elif analysis_type == "exploration":
            display_exploration_results(results)
        
        # Option to generate report
        if st.button("Generate Report from Analysis", key="generate_report_from_analysis"):
            st.session_state.page = "reports"
            st.session_state.reports_action = "generate"
            st.session_state.analysis_results_for_report = results  # Pass results to report page
            st.experimental_rerun()
            
    else:
        st.error(f"Analysis failed: {results.get(\'message\', \'Unknown error\')}")

def display_descriptive_results(results: Dict):
    """Display results from descriptive analysis."""
    st.markdown("### Descriptive Statistics Results")
    
    # Data shape
    if "data_shape" in results:
        st.markdown(f"**Data Shape:** {results[\'data_shape\'].get(\'rows\', \'N/A\')} rows, {results[\'data_shape\'].get(\'columns\', \'N/A\')} columns")
    
    # Summary statistics
    if "summary_statistics" in results:
        st.markdown("#### Summary Statistics")
        summary_df = pd.DataFrame(results["summary_statistics"]).T
        st.dataframe(summary_df)
    
    # Frequency tables
    if "frequency_tables" in results:
        st.markdown("#### Frequency Tables")
        for var, freq_table in results["frequency_tables"].items():
            st.markdown(f"##### {var}")
            freq_df = pd.DataFrame(list(freq_table.items()), columns=["Value", "Frequency"])
            st.dataframe(freq_df)
    
    # Visualizations
    if "visualizations" in results:
        st.markdown("#### Visualizations")
        for viz in results["visualizations"]:
            st.markdown(f"##### {viz.get(\'title\', \'Visualization\')}")
            if "image_base64" in viz and viz["image_base64"] != "...":
                utils.display_image_from_base64(viz["image_base64"], caption=viz.get(\'title\'))
            else:
                # Display a placeholder if image is not available
                st.info("Image placeholder - In a real implementation, the plot would be displayed here.")

def display_inferential_results(results: Dict):
    """Display results from inferential analysis."""
    st.markdown("### Inferential Statistics Results")
    
    if "analyses" in results:
        for analysis in results["analyses"]:
            st.markdown(f"#### {analysis.get(\'type\', \'Analysis\').replace(\'_\', \' \').title()}")
            
            if "result" in analysis:
                st.json(analysis["result"])
            
            if "visualization" in analysis and "image_base64" in analysis["visualization"] and analysis["visualization"]["image_base64"] != "...":
                st.markdown(f"##### {analysis[\'visualization\'].get(\'title\', \'Visualization\')}")
                utils.display_image_from_base64(analysis[\'visualization\']["image_base64"], caption=analysis[\'visualization\'].get(\'title\'))
            else:
                # Display a placeholder if image is not available
                st.info("Image placeholder - In a real implementation, the plot would be displayed here.")

def display_exploration_results(results: Dict):
    """Display results from data exploration."""
    st.markdown("### Data Exploration Results")
    
    # Data shapes
    if "original_data_shape" in results:
        st.markdown(f"**Original Data Shape:** {results[\'original_data_shape\'].get(\'rows\', \'N/A\')} rows, {results[\'original_data_shape\'].get(\'columns\', \'N/A\')} columns")
    
    if "filtered_data_shape" in results:
        st.markdown(f"**Filtered Data Shape:** {results[\'filtered_data_shape\'].get(\'rows\', \'N/A\')} rows, {results[\'filtered_data_shape\'].get(\'columns\', \'N/A\')} columns")
    
    if "grouped_data_shape" in results:
        st.markdown(f"**Grouped Data Shape:** {results[\'grouped_data_shape\'].get(\'rows\', \'N/A\')} rows, {results[\'grouped_data_shape\'].get(\'columns\', \'N/A\')} columns")
    
    # Plot
    if "plot" in results and "image_base64" in results["plot"] and results["plot"]["image_base64"] != "...":
        st.markdown(f"#### {results[\'plot\'].get(\'title\', \'Plot\')}")
        utils.display_image_from_base64(results[\'plot\']["image_base64"], caption=results[\'plot\'].get(\'title\'))
    else:
        # Display a placeholder if image is not available
        st.info("Image placeholder - In a real implementation, the plot would be displayed here.")
    
    # Data preview
    if "data_preview" in results and "preview_data" in results["data_preview"]:
        st.markdown("#### Data Preview (Result of Exploration)")
        preview_data = results["data_preview"]["preview_data"]
        preview_df = pd.DataFrame(preview_data)
        st.dataframe(preview_df)


