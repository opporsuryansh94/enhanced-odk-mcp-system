#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data Exploration Agent for ODK MCP System

This agent is responsible for interactive data exploration of ODK form data.
It provides capabilities for filtering, grouping, pivoting, and visualizing data
to help users gain insights from their collected data.

Author: ODK MCP System
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import requests
from typing import Dict, List, Union, Optional, Any, Tuple
import io
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataExplorationAgent:
    """
    Agent for interactive data exploration of ODK form data.
    
    This agent connects to the Data Aggregation MCP or uses cleaned data from
    the Data Cleaning Agent to provide interactive data exploration capabilities.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the Data Exploration Agent.
        
        Args:
            config_path (str, optional): Path to configuration file. If None, 
                                        uses default configuration.
        """
        self.config = self._load_config(config_path)
        self.daa_mcp_url = self.config.get('daa_mcp_url', 'http://localhost:5003/v1')
        self.auth_token = self.config.get('auth_token')
        
        # Set plot style
        plt.style.use(self.config.get('plot_style', 'seaborn-v0_8-whitegrid'))
        
        # Initialize session for API calls
        self.session = requests.Session()
        if self.auth_token:
            self.session.headers.update({'Authorization': f'Bearer {self.auth_token}'})
        
        # Cache for data
        self._data_cache = {}
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Load configuration from file or use defaults.
        
        Args:
            config_path (str): Path to configuration file.
            
        Returns:
            Dict: Configuration dictionary.
        """
        default_config = {
            'daa_mcp_url': 'http://localhost:5003/v1',
            'auth_token': None,
            'plot_style': 'seaborn-v0_8-whitegrid',
            'default_figsize': (10, 6),
            'default_dpi': 100,
            'color_palette': 'viridis',
            'output_dir': 'output/data_exploration',
            'save_plots': True,
            'show_plots': False,
            'cache_timeout': 300,  # Cache timeout in seconds
            'max_rows_preview': 100,  # Maximum rows to return in preview
            'max_unique_values': 50  # Maximum unique values to return for categorical variables
        }
        
        if not config_path:
            return default_config
        
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Merge user config with defaults
                for key, value in user_config.items():
                    default_config[key] = value
                return default_config
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            return default_config
    
    def fetch_data(self, project_id: str, form_id: Optional[str] = None, 
                  filters: Optional[Dict] = None, use_cleaned: bool = True,
                  force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetch data from Data Aggregation MCP or use cleaned data.
        
        Args:
            project_id (str): Project ID to fetch data for.
            form_id (str, optional): Form ID to filter by.
            filters (Dict, optional): Additional filters to apply.
            use_cleaned (bool): Whether to use cleaned data if available.
            force_refresh (bool): Whether to force refresh the cache.
            
        Returns:
            pd.DataFrame: DataFrame containing the fetched data.
        """
        # Create cache key
        cache_key = f"{project_id}_{form_id}_{json.dumps(filters) if filters else ''}_{use_cleaned}"
        
        # Check cache
        if not force_refresh and cache_key in self._data_cache:
            cache_entry = self._data_cache[cache_key]
            cache_time = cache_entry['timestamp']
            current_time = datetime.now().timestamp()
            
            # If cache is still valid
            if current_time - cache_time < self.config['cache_timeout']:
                return cache_entry['data']
        
        try:
            # If use_cleaned is True, try to get cleaned data from Data Cleaning Agent
            # This would typically be implemented as a direct call to the Data Cleaning Agent
            # or by retrieving cleaned data from a shared storage location
            
            # For now, we'll simulate by calling the Data Aggregation MCP directly
            url = f"{self.daa_mcp_url}/projects/{project_id}/data"
            params = {}
            
            if form_id:
                params['form_id'] = form_id
            
            if filters:
                for key, value in filters.items():
                    params[key] = value
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract submission data from each record
            records = []
            for item in data.get('data', []):
                submission_data = item.get('data', {})
                # Add metadata fields
                submission_data['_submission_id'] = item.get('submission_id')
                submission_data['_instance_id'] = item.get('instance_id')
                submission_data['_submitted_by'] = item.get('submitted_by')
                submission_data['_submitted_at'] = item.get('submitted_at')
                records.append(submission_data)
            
            if not records:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            
            # If use_cleaned is True, we would apply some basic cleaning here
            # In a real implementation, this would be handled by the Data Cleaning Agent
            if use_cleaned:
                # Basic cleaning: convert data types
                for col in df.columns:
                    # Try to convert numeric columns
                    try:
                        if df[col].dtype == 'object':
                            df[col] = pd.to_numeric(df[col], errors='ignore')
                    except:
                        pass
                    
                    # Try to convert date columns
                    try:
                        if col.endswith('_date') or '_date_' in col:
                            df[col] = pd.to_datetime(df[col], errors='ignore')
                    except:
                        pass
            
            # Update cache
            self._data_cache[cache_key] = {
                'data': df,
                'timestamp': datetime.now().timestamp()
            }
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            raise
    
    def get_data_preview(self, df: pd.DataFrame, n_rows: int = None) -> Dict:
        """
        Get a preview of the data.
        
        Args:
            df (pd.DataFrame): DataFrame to preview.
            n_rows (int, optional): Number of rows to include in preview.
            
        Returns:
            Dict: Data preview information.
        """
        if df.empty:
            return {
                'status': 'error',
                'message': 'Empty DataFrame'
            }
        
        try:
            if n_rows is None:
                n_rows = min(self.config['max_rows_preview'], len(df))
            else:
                n_rows = min(n_rows, len(df))
            
            # Get preview rows
            preview_df = df.head(n_rows)
            
            # Get column information
            columns_info = []
            for col in df.columns:
                col_info = {
                    'name': col,
                    'dtype': str(df[col].dtype),
                    'non_null_count': int(df[col].count()),
                    'null_count': int(df[col].isna().sum()),
                    'unique_count': int(df[col].nunique())
                }
                
                # Add sample values for categorical columns
                if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col]):
                    unique_values = df[col].dropna().unique()
                    if len(unique_values) <= self.config['max_unique_values']:
                        col_info['unique_values'] = [str(val) for val in unique_values]
                
                # Add min/max for numeric columns
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_info['min'] = float(df[col].min()) if not df[col].empty else None
                    col_info['max'] = float(df[col].max()) if not df[col].empty else None
                
                # Add min/max for datetime columns
                if pd.api.types.is_datetime64_dtype(df[col]):
                    col_info['min'] = df[col].min().isoformat() if not df[col].empty else None
                    col_info['max'] = df[col].max().isoformat() if not df[col].empty else None
                
                columns_info.append(col_info)
            
            # Convert preview to records
            preview_records = preview_df.to_dict(orient='records')
            
            # Create result
            result = {
                'status': 'success',
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'preview_rows': n_rows,
                'columns': columns_info,
                'preview_data': preview_records
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting data preview: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def filter_data(self, df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        """
        Filter data based on specified conditions.
        
        Args:
            df (pd.DataFrame): DataFrame to filter.
            filters (Dict): Filter conditions.
                Format: {
                    'column1': {'operator': '==', 'value': 'value1'},
                    'column2': {'operator': '>', 'value': 100},
                    ...
                }
                Supported operators: ==, !=, >, >=, <, <=, in, not_in, contains, starts_with, ends_with
            
        Returns:
            pd.DataFrame: Filtered DataFrame.
        """
        if df.empty:
            return df
        
        if not filters:
            return df
        
        try:
            filtered_df = df.copy()
            
            for column, condition in filters.items():
                if column not in filtered_df.columns:
                    logger.warning(f"Column {column} not found in DataFrame")
                    continue
                
                operator = condition.get('operator')
                value = condition.get('value')
                
                if operator == '==':
                    filtered_df = filtered_df[filtered_df[column] == value]
                elif operator == '!=':
                    filtered_df = filtered_df[filtered_df[column] != value]
                elif operator == '>':
                    filtered_df = filtered_df[filtered_df[column] > value]
                elif operator == '>=':
                    filtered_df = filtered_df[filtered_df[column] >= value]
                elif operator == '<':
                    filtered_df = filtered_df[filtered_df[column] < value]
                elif operator == '<=':
                    filtered_df = filtered_df[filtered_df[column] <= value]
                elif operator == 'in':
                    if isinstance(value, list):
                        filtered_df = filtered_df[filtered_df[column].isin(value)]
                elif operator == 'not_in':
                    if isinstance(value, list):
                        filtered_df = filtered_df[~filtered_df[column].isin(value)]
                elif operator == 'contains':
                    if pd.api.types.is_string_dtype(filtered_df[column]):
                        filtered_df = filtered_df[filtered_df[column].str.contains(str(value), na=False)]
                elif operator == 'starts_with':
                    if pd.api.types.is_string_dtype(filtered_df[column]):
                        filtered_df = filtered_df[filtered_df[column].str.startswith(str(value), na=False)]
                elif operator == 'ends_with':
                    if pd.api.types.is_string_dtype(filtered_df[column]):
                        filtered_df = filtered_df[filtered_df[column].str.endswith(str(value), na=False)]
                elif operator == 'is_null':
                    filtered_df = filtered_df[filtered_df[column].isna()]
                elif operator == 'is_not_null':
                    filtered_df = filtered_df[~filtered_df[column].isna()]
                else:
                    logger.warning(f"Unsupported operator: {operator}")
            
            return filtered_df
            
        except Exception as e:
            logger.error(f"Error filtering data: {e}")
            return df
    
    def group_by(self, df: pd.DataFrame, group_columns: List[str], 
                agg_columns: Dict[str, List[str]]) -> pd.DataFrame:
        """
        Group data by specified columns and aggregate.
        
        Args:
            df (pd.DataFrame): DataFrame to group.
            group_columns (List[str]): Columns to group by.
            agg_columns (Dict[str, List[str]]): Columns to aggregate with aggregation functions.
                Format: {
                    'column1': ['mean', 'sum', 'count'],
                    'column2': ['min', 'max'],
                    ...
                }
            
        Returns:
            pd.DataFrame: Grouped DataFrame.
        """
        if df.empty:
            return df
        
        if not group_columns:
            return df
        
        try:
            # Check if all group columns exist
            missing_cols = [col for col in group_columns if col not in df.columns]
            if missing_cols:
                logger.warning(f"Group columns not found: {', '.join(missing_cols)}")
                return df
            
            # Prepare aggregation dictionary
            agg_dict = {}
            for col, funcs in agg_columns.items():
                if col in df.columns:
                    agg_dict[col] = funcs
            
            if not agg_dict:
                # If no aggregation specified, use count for all columns
                for col in df.columns:
                    if col not in group_columns:
                        agg_dict[col] = ['count']
            
            # Group and aggregate
            grouped_df = df.groupby(group_columns).agg(agg_dict)
            
            # Flatten multi-level column index
            grouped_df.columns = ['_'.join(col).strip() for col in grouped_df.columns.values]
            
            # Reset index to make group columns regular columns
            grouped_df = grouped_df.reset_index()
            
            return grouped_df
            
        except Exception as e:
            logger.error(f"Error grouping data: {e}")
            return df
    
    def pivot_table(self, df: pd.DataFrame, index: List[str], 
                   columns: Optional[str] = None, 
                   values: Optional[str] = None,
                   aggfunc: str = 'mean') -> pd.DataFrame:
        """
        Create a pivot table.
        
        Args:
            df (pd.DataFrame): DataFrame to pivot.
            index (List[str]): Columns to use as index.
            columns (str, optional): Column to use for pivot columns.
            values (str, optional): Column to use for values.
            aggfunc (str): Aggregation function.
            
        Returns:
            pd.DataFrame: Pivot table.
        """
        if df.empty:
            return df
        
        if not index:
            return df
        
        try:
            # Check if all required columns exist
            all_cols = index.copy()
            if columns:
                all_cols.append(columns)
            if values:
                all_cols.append(values)
            
            missing_cols = [col for col in all_cols if col not in df.columns]
            if missing_cols:
                logger.warning(f"Columns not found: {', '.join(missing_cols)}")
                return df
            
            # Create pivot table
            pivot_df = pd.pivot_table(
                df,
                index=index,
                columns=columns,
                values=values,
                aggfunc=aggfunc,
                fill_value=0
            )
            
            # Reset index to make index columns regular columns
            pivot_df = pivot_df.reset_index()
            
            return pivot_df
            
        except Exception as e:
            logger.error(f"Error creating pivot table: {e}")
            return df
    
    def interactive_plot(self, df: pd.DataFrame, plot_type: str,
                        x: Optional[str] = None, y: Optional[str] = None,
                        hue: Optional[str] = None, title: Optional[str] = None,
                        figsize: Optional[Tuple[int, int]] = None,
                        **kwargs) -> Dict:
        """
        Create an interactive plot.
        
        Args:
            df (pd.DataFrame): DataFrame to plot.
            plot_type (str): Type of plot ('bar', 'line', 'scatter', 'box', 'hist', 'heatmap', 'pie').
            x (str, optional): Column for x-axis.
            y (str, optional): Column for y-axis.
            hue (str, optional): Column for color grouping.
            title (str, optional): Plot title.
            figsize (Tuple[int, int], optional): Figure size.
            **kwargs: Additional plot-specific parameters.
            
        Returns:
            Dict: Plot information with base64-encoded image.
        """
        if df.empty:
            return {'error': "DataFrame is empty"}
        
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=figsize or self.config['default_figsize'])
            
            # Create plot based on type
            if plot_type == 'bar':
                if x is None or y is None:
                    return {'error': "Both x and y must be specified for bar plot"}
                
                if x not in df.columns or y not in df.columns:
                    return {'error': f"Columns not found: {x if x not in df.columns else y}"}
                
                if hue and hue in df.columns:
                    sns.barplot(x=x, y=y, hue=hue, data=df, ax=ax)
                else:
                    sns.barplot(x=x, y=y, data=df, ax=ax)
            
            elif plot_type == 'line':
                if x is None or y is None:
                    return {'error': "Both x and y must be specified for line plot"}
                
                if x not in df.columns or y not in df.columns:
                    return {'error': f"Columns not found: {x if x not in df.columns else y}"}
                
                if hue and hue in df.columns:
                    sns.lineplot(x=x, y=y, hue=hue, data=df, ax=ax)
                else:
                    sns.lineplot(x=x, y=y, data=df, ax=ax)
            
            elif plot_type == 'scatter':
                if x is None or y is None:
                    return {'error': "Both x and y must be specified for scatter plot"}
                
                if x not in df.columns or y not in df.columns:
                    return {'error': f"Columns not found: {x if x not in df.columns else y}"}
                
                if hue and hue in df.columns:
                    sns.scatterplot(x=x, y=y, hue=hue, data=df, ax=ax)
                else:
                    sns.scatterplot(x=x, y=y, data=df, ax=ax)
            
            elif plot_type == 'box':
                if x is None and y is None:
                    return {'error': "At least one of x or y must be specified for box plot"}
                
                if x and x not in df.columns:
                    return {'error': f"Column not found: {x}"}
                
                if y and y not in df.columns:
                    return {'error': f"Column not found: {y}"}
                
                if hue and hue in df.columns:
                    sns.boxplot(x=x, y=y, hue=hue, data=df, ax=ax)
                else:
                    sns.boxplot(x=x, y=y, data=df, ax=ax)
            
            elif plot_type == 'hist':
                if x is None:
                    return {'error': "x must be specified for histogram"}
                
                if x not in df.columns:
                    return {'error': f"Column not found: {x}"}
                
                bins = kwargs.get('bins', 10)
                kde = kwargs.get('kde', True)
                
                if hue and hue in df.columns:
                    sns.histplot(x=x, hue=hue, data=df, bins=bins, kde=kde, ax=ax)
                else:
                    sns.histplot(x=x, data=df, bins=bins, kde=kde, ax=ax)
            
            elif plot_type == 'heatmap':
                # For heatmap, we need a pivot table or correlation matrix
                if 'data_matrix' in kwargs:
                    data_matrix = kwargs['data_matrix']
                    sns.heatmap(data_matrix, annot=kwargs.get('annot', True), 
                               cmap=kwargs.get('cmap', 'viridis'), ax=ax)
                else:
                    # Create correlation matrix if not provided
                    corr_matrix = df.select_dtypes(include=['number']).corr()
                    sns.heatmap(corr_matrix, annot=kwargs.get('annot', True), 
                               cmap=kwargs.get('cmap', 'viridis'), ax=ax)
            
            elif plot_type == 'pie':
                if x is None:
                    return {'error': "x must be specified for pie chart"}
                
                if x not in df.columns:
                    return {'error': f"Column not found: {x}"}
                
                # Get value counts
                value_counts = df[x].value_counts()
                
                # Limit to top categories if too many
                max_categories = kwargs.get('max_categories', 8)
                if len(value_counts) > max_categories:
                    other_count = value_counts.iloc[max_categories:].sum()
                    value_counts = value_counts.iloc[:max_categories]
                    value_counts['Other'] = other_count
                
                # Create pie chart
                ax.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%',
                      shadow=kwargs.get('shadow', False), startangle=kwargs.get('startangle', 90))
                ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            
            else:
                return {'error': f"Unsupported plot type: {plot_type}"}
            
            # Set title
            if title:
                ax.set_title(title)
            
            # Adjust layout
            fig.tight_layout()
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"{plot_type}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            # Create result
            result = {
                'plot_type': plot_type,
                'x': x,
                'y': y,
                'hue': hue,
                'title': title,
                'image_base64': img_base64
            }
            
            if plot_path:
                result['file_path'] = plot_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating plot: {e}")
            return {'error': str(e)}
    
    def explore_data(self, project_id: str, form_id: Optional[str] = None,
                    exploration_config: Dict = None) -> Dict:
        """
        Explore data based on specified configuration.
        
        Args:
            project_id (str): Project ID.
            form_id (str, optional): Form ID.
            exploration_config (Dict): Exploration configuration.
                Format: {
                    'filters': {...},
                    'group_by': {
                        'columns': [...],
                        'aggregations': {...}
                    },
                    'pivot': {
                        'index': [...],
                        'columns': '...',
                        'values': '...',
                        'aggfunc': '...'
                    },
                    'plot': {
                        'type': '...',
                        'x': '...',
                        'y': '...',
                        'hue': '...',
                        'title': '...',
                        ...
                    }
                }
            
        Returns:
            Dict: Exploration results.
        """
        try:
            # Fetch data
            df = self.fetch_data(project_id, form_id)
            
            if df.empty:
                return {
                    'status': 'error',
                    'message': 'No data found',
                    'project_id': project_id,
                    'form_id': form_id,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Initialize result
            result = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'project_id': project_id,
                'form_id': form_id,
                'original_data_shape': {
                    'rows': len(df),
                    'columns': len(df.columns)
                }
            }
            
            # Apply exploration steps if config provided
            if exploration_config:
                # Apply filters
                if 'filters' in exploration_config:
                    df = self.filter_data(df, exploration_config['filters'])
                    result['filtered_data_shape'] = {
                        'rows': len(df),
                        'columns': len(df.columns)
                    }
                
                # Apply grouping
                if 'group_by' in exploration_config:
                    group_config = exploration_config['group_by']
                    if 'columns' in group_config:
                        df = self.group_by(
                            df,
                            group_config['columns'],
                            group_config.get('aggregations', {})
                        )
                        result['grouped_data_shape'] = {
                            'rows': len(df),
                            'columns': len(df.columns)
                        }
                
                # Apply pivot
                if 'pivot' in exploration_config:
                    pivot_config = exploration_config['pivot']
                    if 'index' in pivot_config:
                        df = self.pivot_table(
                            df,
                            pivot_config['index'],
                            pivot_config.get('columns'),
                            pivot_config.get('values'),
                            pivot_config.get('aggfunc', 'mean')
                        )
                        result['pivoted_data_shape'] = {
                            'rows': len(df),
                            'columns': len(df.columns)
                        }
                
                # Create plot
                if 'plot' in exploration_config:
                    plot_config = exploration_config['plot']
                    if 'type' in plot_config:
                        plot_type = plot_config.pop('type')
                        plot_result = self.interactive_plot(df, plot_type, **plot_config)
                        result['plot'] = plot_result
            
            # Get data preview
            result['data_preview'] = self.get_data_preview(df)
            
            return result
            
        except Exception as e:
            logger.error(f"Error exploring data: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'project_id': project_id,
                'form_id': form_id,
                'timestamp': datetime.now().isoformat()
            }

# Example usage
if __name__ == "__main__":
    # This would be called by the agent framework or directly
    agent = DataExplorationAgent()
    
    # Example exploration
    result = agent.explore_data(
        project_id="sample_project",
        form_id="sample_form",
        exploration_config={
            'filters': {
                'age': {'operator': '>', 'value': 18}
            },
            'group_by': {
                'columns': ['gender'],
                'aggregations': {
                    'age': ['mean', 'count']
                }
            },
            'plot': {
                'type': 'bar',
                'x': 'gender',
                'y': 'age_mean',
                'title': 'Average Age by Gender'
            }
        }
    )
    
    print(json.dumps(result, indent=2))

