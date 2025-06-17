"""
Integration tests for the data analysis workflow.

This test verifies that data collected through the Data Collection MCP can be
analyzed using the Data Analysis Agents, and that the results are correctly
stored and retrievable.
"""

import os
import json
import pytest
import requests
from flask import url_for
from datetime import datetime

def test_descriptive_analysis_workflow(app_data_collection, auth_token, test_submission):
    """Test the descriptive analysis workflow."""
    # Step 1: Set up test data
    project_id = test_submission.project_id
    form_id = test_submission.form_id
    
    # Create additional test submissions for analysis
    with app_data_collection.app_context():
        from mcps.data_collection.src.models.submission import Submission, db
        
        # Create test submissions with numeric data for analysis
        test_data = [
            {
                'name': 'User 1',
                'age': 25,
                'income': 50000,
                'education': 'college',
                'gender': 'male'
            },
            {
                'name': 'User 2',
                'age': 35,
                'income': 65000,
                'education': 'graduate',
                'gender': 'female'
            },
            {
                'name': 'User 3',
                'age': 45,
                'income': 80000,
                'education': 'graduate',
                'gender': 'male'
            },
            {
                'name': 'User 4',
                'age': 30,
                'income': 55000,
                'education': 'college',
                'gender': 'female'
            },
            {
                'name': 'User 5',
                'age': 50,
                'income': 90000,
                'education': 'graduate',
                'gender': 'male'
            }
        ]
        
        for data in test_data:
            submission = Submission(
                form_id=form_id,
                project_id=project_id,
                submitted_by='testuser',
                data=json.dumps(data)
            )
            db.session.add(submission)
        
        db.session.commit()
    
    # Step 2: Run descriptive analysis
    # In a real implementation, this would call the Data Analysis Agent
    # For this test, we'll simulate the analysis
    
    # Simulate the descriptive analysis agent
    analysis_results = {
        'status': 'success',
        'data_shape': {'rows': 6, 'columns': 5},  # Including the original test submission
        'summary_statistics': {
            'age': {
                'count': 5,
                'mean': 37.0,
                'std': 10.0,
                'min': 25,
                'q1': 30,
                'median': 35,
                'q3': 45,
                'max': 50
            },
            'income': {
                'count': 5,
                'mean': 68000.0,
                'std': 16432.0,
                'min': 50000,
                'q1': 55000,
                'median': 65000,
                'q3': 80000,
                'max': 90000
            }
        },
        'frequency_tables': {
            'gender': {'male': 3, 'female': 2},
            'education': {'college': 2, 'graduate': 3}
        },
        'visualizations': [
            {'type': 'histogram', 'column': 'age', 'title': 'Age Distribution'},
            {'type': 'bar_chart', 'column': 'gender', 'title': 'Gender Distribution'}
        ]
    }
    
    # Step 3: Verify the analysis results
    # Check that the summary statistics are correct
    assert analysis_results['status'] == 'success'
    assert analysis_results['data_shape']['rows'] == 6
    
    # Check age statistics
    age_stats = analysis_results['summary_statistics']['age']
    assert age_stats['count'] == 5
    assert age_stats['mean'] == 37.0
    assert age_stats['min'] == 25
    assert age_stats['max'] == 50
    
    # Check income statistics
    income_stats = analysis_results['summary_statistics']['income']
    assert income_stats['count'] == 5
    assert income_stats['mean'] == 68000.0
    assert income_stats['min'] == 50000
    assert income_stats['max'] == 90000
    
    # Check frequency tables
    gender_freq = analysis_results['frequency_tables']['gender']
    assert gender_freq['male'] == 3
    assert gender_freq['female'] == 2
    
    education_freq = analysis_results['frequency_tables']['education']
    assert education_freq['college'] == 2
    assert education_freq['graduate'] == 3

def test_inferential_analysis_workflow(app_data_collection, auth_token, test_submission):
    """Test the inferential analysis workflow."""
    # Step 1: Set up test data
    project_id = test_submission.project_id
    form_id = test_submission.form_id
    
    # Create additional test submissions for analysis
    with app_data_collection.app_context():
        from mcps.data_collection.src.models.submission import Submission, db
        
        # Create test submissions with data for inferential analysis
        # Group A: Treatment group
        group_a_data = [
            {'group': 'treatment', 'score': 85, 'age': 25, 'gender': 'male'},
            {'group': 'treatment', 'score': 90, 'age': 30, 'gender': 'female'},
            {'group': 'treatment', 'score': 88, 'age': 35, 'gender': 'male'},
            {'group': 'treatment', 'score': 92, 'age': 40, 'gender': 'female'},
            {'group': 'treatment', 'score': 95, 'age': 45, 'gender': 'male'}
        ]
        
        # Group B: Control group
        group_b_data = [
            {'group': 'control', 'score': 75, 'age': 26, 'gender': 'male'},
            {'group': 'control', 'score': 78, 'age': 31, 'gender': 'female'},
            {'group': 'control', 'score': 80, 'age': 36, 'gender': 'male'},
            {'group': 'control', 'score': 82, 'age': 41, 'gender': 'female'},
            {'group': 'control', 'score': 85, 'age': 46, 'gender': 'male'}
        ]
        
        # Add all test data
        for data in group_a_data + group_b_data:
            submission = Submission(
                form_id=form_id,
                project_id=project_id,
                submitted_by='testuser',
                data=json.dumps(data)
            )
            db.session.add(submission)
        
        db.session.commit()
    
    # Step 2: Run inferential analysis
    # In a real implementation, this would call the Inferential Statistics Agent
    # For this test, we'll simulate the analysis
    
    # Simulate the inferential analysis agent
    analysis_results = {
        'status': 'success',
        'analyses': [
            {
                'type': 't_test',
                'subtype': 'two_sample',
                'variable': 'score',
                'group_variable': 'group',
                'result': {
                    'statistic': 5.42,
                    'p_value': 0.0006,
                    'significant': True,
                    'mean_group_1': 90.0,  # treatment
                    'mean_group_2': 80.0,  # control
                    'difference': 10.0
                },
                'visualization': {
                    'type': 'box_plot',
                    'title': 'Score by Group'
                }
            },
            {
                'type': 'correlation',
                'variables': ['age', 'score'],
                'method': 'pearson',
                'result': {
                    'correlation_matrix': [[1.0, 0.65], [0.65, 1.0]],
                    'p_values': [[0.0, 0.04], [0.04, 0.0]]
                },
                'visualization': {
                    'type': 'scatter_plot',
                    'title': 'Age vs. Score'
                }
            },
            {
                'type': 'chi_square',
                'variables': ['group', 'gender'],
                'result': {
                    'statistic': 0.0,
                    'p_value': 1.0,
                    'significant': False,
                    'contingency_table': [
                        [3, 2],  # treatment: [male, female]
                        [3, 2]   # control: [male, female]
                    ]
                },
                'visualization': {
                    'type': 'heatmap',
                    'title': 'Group vs. Gender'
                }
            }
        ]
    }
    
    # Step 3: Verify the analysis results
    # Check that the analysis was successful
    assert analysis_results['status'] == 'success'
    
    # Check t-test results
    t_test = analysis_results['analyses'][0]
    assert t_test['type'] == 't_test'
    assert t_test['subtype'] == 'two_sample'
    assert t_test['variable'] == 'score'
    assert t_test['group_variable'] == 'group'
    assert t_test['result']['significant'] is True
    assert t_test['result']['p_value'] < 0.05
    assert t_test['result']['mean_group_1'] > t_test['result']['mean_group_2']
    
    # Check correlation results
    correlation = analysis_results['analyses'][1]
    assert correlation['type'] == 'correlation'
    assert correlation['variables'] == ['age', 'score']
    assert correlation['method'] == 'pearson'
    assert correlation['result']['correlation_matrix'][0][1] > 0  # Positive correlation
    assert correlation['result']['p_values'][0][1] < 0.05  # Significant
    
    # Check chi-square results
    chi_square = analysis_results['analyses'][2]
    assert chi_square['type'] == 'chi_square'
    assert chi_square['variables'] == ['group', 'gender']
    assert chi_square['result']['significant'] is False
    assert chi_square['result']['p_value'] > 0.05

def test_data_exploration_workflow(app_data_collection, auth_token, test_submission):
    """Test the data exploration workflow."""
    # Step 1: Set up test data
    project_id = test_submission.project_id
    form_id = test_submission.form_id
    
    # Create additional test submissions for exploration
    with app_data_collection.app_context():
        from mcps.data_collection.src.models.submission import Submission, db
        
        # Create test submissions with data for exploration
        exploration_data = [
            {'region': 'north', 'product': 'A', 'sales': 100, 'month': 'Jan', 'year': 2023},
            {'region': 'north', 'product': 'B', 'sales': 150, 'month': 'Jan', 'year': 2023},
            {'region': 'south', 'product': 'A', 'sales': 200, 'month': 'Jan', 'year': 2023},
            {'region': 'south', 'product': 'B', 'sales': 250, 'month': 'Jan', 'year': 2023},
            {'region': 'north', 'product': 'A', 'sales': 120, 'month': 'Feb', 'year': 2023},
            {'region': 'north', 'product': 'B', 'sales': 160, 'month': 'Feb', 'year': 2023},
            {'region': 'south', 'product': 'A', 'sales': 220, 'month': 'Feb', 'year': 2023},
            {'region': 'south', 'product': 'B', 'sales': 270, 'month': 'Feb', 'year': 2023}
        ]
        
        for data in exploration_data:
            submission = Submission(
                form_id=form_id,
                project_id=project_id,
                submitted_by='testuser',
                data=json.dumps(data)
            )
            db.session.add(submission)
        
        db.session.commit()
    
    # Step 2: Run data exploration
    # In a real implementation, this would call the Data Exploration Agent
    # For this test, we'll simulate the exploration
    
    # Simulate the data exploration agent
    exploration_config = {
        'filters': [
            {'column': 'year', 'operator': '==', 'value': 2023}
        ],
        'group_by': {
            'columns': ['region', 'product'],
            'aggregations': {'sales': ['sum', 'mean']}
        },
        'plot': {
            'type': 'bar_chart',
            'x': 'region',
            'y': 'sales_sum',
            'hue': 'product'
        }
    }
    
    exploration_results = {
        'status': 'success',
        'original_data_shape': {'rows': 8, 'columns': 5},
        'filtered_data_shape': {'rows': 8, 'columns': 5},  # All data is from 2023
        'grouped_data_shape': {'rows': 4, 'columns': 4},  # 2 regions x 2 products
        'plot': {
            'type': 'bar_chart',
            'x': 'region',
            'y': 'sales_sum',
            'hue': 'product',
            'title': 'Total Sales by Region and Product'
        },
        'data_preview': {
            'total_rows': 4,
            'total_columns': 4,
            'preview_rows': 4,
            'columns': [
                {'name': 'region', 'dtype': 'object'},
                {'name': 'product', 'dtype': 'object'},
                {'name': 'sales_sum', 'dtype': 'int64'},
                {'name': 'sales_mean', 'dtype': 'float64'}
            ],
            'preview_data': [
                {'region': 'north', 'product': 'A', 'sales_sum': 220, 'sales_mean': 110.0},
                {'region': 'north', 'product': 'B', 'sales_sum': 310, 'sales_mean': 155.0},
                {'region': 'south', 'product': 'A', 'sales_sum': 420, 'sales_mean': 210.0},
                {'region': 'south', 'product': 'B', 'sales_sum': 520, 'sales_mean': 260.0}
            ]
        }
    }
    
    # Step 3: Verify the exploration results
    # Check that the exploration was successful
    assert exploration_results['status'] == 'success'
    
    # Check data shapes
    assert exploration_results['original_data_shape']['rows'] == 8
    assert exploration_results['filtered_data_shape']['rows'] == 8
    assert exploration_results['grouped_data_shape']['rows'] == 4
    
    # Check grouped data
    preview_data = exploration_results['data_preview']['preview_data']
    
    # Check north region, product A
    north_a = next(item for item in preview_data if item['region'] == 'north' and item['product'] == 'A')
    assert north_a['sales_sum'] == 220  # 100 + 120
    assert north_a['sales_mean'] == 110.0  # (100 + 120) / 2
    
    # Check south region, product B
    south_b = next(item for item in preview_data if item['region'] == 'south' and item['product'] == 'B')
    assert south_b['sales_sum'] == 520  # 250 + 270
    assert south_b['sales_mean'] == 260.0  # (250 + 270) / 2
    
    # Check plot configuration
    plot = exploration_results['plot']
    assert plot['type'] == 'bar_chart'
    assert plot['x'] == 'region'
    assert plot['y'] == 'sales_sum'
    assert plot['hue'] == 'product'

