#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Descriptive Analytics Agent for ODK MCP System

This agent is responsible for performing descriptive statistical analysis on cleaned data.
It generates summary statistics, frequency distributions, and visualizations to provide
insights into the data collected through ODK forms.

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

class DescriptiveAnalyticsAgent:
    """
    Agent for performing descriptive analytics on ODK form data.
    
    This agent connects to the Data Aggregation MCP or uses cleaned data from
    the Data Cleaning Agent to generate descriptive statistics and visualizations.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the Descriptive Analytics Agent.
        
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
            'max_categories_pie': 8,
            'max_categories_bar': 15,
            'output_dir': 'output/descriptive_analytics',
            'save_plots': True,
            'show_plots': False
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
                  filters: Optional[Dict] = None, use_cleaned: bool = True) -> pd.DataFrame:
        """
        Fetch data from Data Aggregation MCP or use cleaned data.
        
        Args:
            project_id (str): Project ID to fetch data for.
            form_id (str, optional): Form ID to filter by.
            filters (Dict, optional): Additional filters to apply.
            use_cleaned (bool): Whether to use cleaned data if available.
            
        Returns:
            pd.DataFrame: DataFrame containing the fetched data.
        """
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
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            raise
    
    def calculate_summary_stats(self, df: pd.DataFrame, 
                              numeric_only: bool = True) -> Dict[str, Dict[str, float]]:
        """
        Calculate summary statistics for each column in the DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze.
            numeric_only (bool): Whether to include only numeric columns.
            
        Returns:
            Dict[str, Dict[str, float]]: Dictionary of summary statistics by column.
        """
        if df.empty:
            return {}
        
        result = {}
        
        # Select columns based on numeric_only flag
        if numeric_only:
            columns = df.select_dtypes(include=['number']).columns
        else:
            columns = df.columns
        
        for col in columns:
            # Skip metadata columns
            if col.startswith('_'):
                continue
                
            col_stats = {}
            
            # For numeric columns, calculate standard statistics
            if pd.api.types.is_numeric_dtype(df[col]):
                col_stats = {
                    'count': int(df[col].count()),
                    'missing': int(df[col].isna().sum()),
                    'mean': float(df[col].mean()) if not df[col].empty else None,
                    'std': float(df[col].std()) if not df[col].empty else None,
                    'min': float(df[col].min()) if not df[col].empty else None,
                    'q1': float(df[col].quantile(0.25)) if not df[col].empty else None,
                    'median': float(df[col].median()) if not df[col].empty else None,
                    'q3': float(df[col].quantile(0.75)) if not df[col].empty else None,
                    'max': float(df[col].max()) if not df[col].empty else None,
                    'iqr': float(df[col].quantile(0.75) - df[col].quantile(0.25)) if not df[col].empty else None,
                    'skew': float(df[col].skew()) if not df[col].empty else None,
                    'kurtosis': float(df[col].kurtosis()) if not df[col].empty else None
                }
            # For datetime columns, calculate temporal statistics
            elif pd.api.types.is_datetime64_dtype(df[col]):
                col_stats = {
                    'count': int(df[col].count()),
                    'missing': int(df[col].isna().sum()),
                    'min': df[col].min().isoformat() if not df[col].empty else None,
                    'max': df[col].max().isoformat() if not df[col].empty else None,
                    'range_days': float((df[col].max() - df[col].min()).days) if not df[col].empty else None
                }
            # For categorical/string columns, calculate basic counts
            elif not numeric_only:
                col_stats = {
                    'count': int(df[col].count()),
                    'missing': int(df[col].isna().sum()),
                    'unique': int(df[col].nunique()),
                    'top': str(df[col].mode()[0]) if not df[col].empty and not df[col].mode().empty else None,
                    'freq': int(df[col].value_counts().iloc[0]) if not df[col].empty and not df[col].value_counts().empty else None
                }
            
            if col_stats:
                result[col] = col_stats
        
        return result
    
    def generate_frequency_tables(self, df: pd.DataFrame, 
                                columns: Optional[List[str]] = None,
                                max_categories: int = 20) -> Dict[str, Dict[str, int]]:
        """
        Generate frequency tables for categorical columns.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze.
            columns (List[str], optional): List of columns to include. If None, uses all categorical columns.
            max_categories (int): Maximum number of categories to include in each table.
            
        Returns:
            Dict[str, Dict[str, int]]: Dictionary of frequency tables by column.
        """
        if df.empty:
            return {}
        
        result = {}
        
        # Select columns
        if columns:
            selected_columns = [col for col in columns if col in df.columns]
        else:
            # Use object, category, and boolean columns
            selected_columns = df.select_dtypes(include=['object', 'category', 'bool']).columns
        
        for col in selected_columns:
            # Skip metadata columns
            if col.startswith('_'):
                continue
                
            # Get value counts
            value_counts = df[col].value_counts().head(max_categories)
            
            # Convert to dictionary
            freq_table = {str(k): int(v) for k, v in value_counts.items()}
            
            # Add "Other" category if there are more categories than max_categories
            if df[col].nunique() > max_categories:
                other_count = df[col].value_counts().iloc[max_categories:].sum()
                freq_table['Other'] = int(other_count)
            
            result[col] = freq_table
        
        return result
    
    def plot_histogram(self, df: pd.DataFrame, column: str, 
                      bins: int = 20, kde: bool = True,
                      title: Optional[str] = None,
                      figsize: Optional[Tuple[int, int]] = None) -> Dict:
        """
        Create a histogram for a numeric column.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze.
            column (str): Column to plot.
            bins (int): Number of bins for histogram.
            kde (bool): Whether to include KDE curve.
            title (str, optional): Plot title. If None, uses column name.
            figsize (Tuple[int, int], optional): Figure size. If None, uses default.
            
        Returns:
            Dict: Dictionary with plot information and base64-encoded image.
        """
        if df.empty or column not in df.columns:
            return {'error': f"Column {column} not found or DataFrame is empty"}
        
        if not pd.api.types.is_numeric_dtype(df[column]):
            return {'error': f"Column {column} is not numeric"}
        
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=figsize or self.config['default_figsize'])
            
            # Plot histogram with KDE
            sns.histplot(df[column].dropna(), bins=bins, kde=kde, ax=ax)
            
            # Set title and labels
            ax.set_title(title or f"Distribution of {column}")
            ax.set_xlabel(column)
            ax.set_ylabel("Frequency")
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Tight layout
            fig.tight_layout()
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"histogram_{column}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            # Return plot information
            result = {
                'type': 'histogram',
                'column': column,
                'bins': bins,
                'kde': kde,
                'title': title or f"Distribution of {column}",
                'image_base64': img_base64
            }
            
            if plot_path:
                result['file_path'] = plot_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating histogram for {column}: {e}")
            return {'error': str(e)}
    
    def plot_boxplot(self, df: pd.DataFrame, column: str,
                    title: Optional[str] = None,
                    figsize: Optional[Tuple[int, int]] = None) -> Dict:
        """
        Create a boxplot for a numeric column.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze.
            column (str): Column to plot.
            title (str, optional): Plot title. If None, uses column name.
            figsize (Tuple[int, int], optional): Figure size. If None, uses default.
            
        Returns:
            Dict: Dictionary with plot information and base64-encoded image.
        """
        if df.empty or column not in df.columns:
            return {'error': f"Column {column} not found or DataFrame is empty"}
        
        if not pd.api.types.is_numeric_dtype(df[column]):
            return {'error': f"Column {column} is not numeric"}
        
        try:
            # Create figure
            fig, ax = plt.subplots(figsize=figsize or self.config['default_figsize'])
            
            # Plot boxplot
            sns.boxplot(x=df[column].dropna(), ax=ax)
            
            # Set title and labels
            ax.set_title(title or f"Boxplot of {column}")
            ax.set_xlabel(column)
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Tight layout
            fig.tight_layout()
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"boxplot_{column}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            # Return plot information
            result = {
                'type': 'boxplot',
                'column': column,
                'title': title or f"Boxplot of {column}",
                'image_base64': img_base64
            }
            
            if plot_path:
                result['file_path'] = plot_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating boxplot for {column}: {e}")
            return {'error': str(e)}
    
    def plot_bar_chart(self, df: pd.DataFrame, column: str,
                      max_categories: int = None,
                      title: Optional[str] = None,
                      figsize: Optional[Tuple[int, int]] = None) -> Dict:
        """
        Create a bar chart for a categorical column.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze.
            column (str): Column to plot.
            max_categories (int, optional): Maximum number of categories to include.
            title (str, optional): Plot title. If None, uses column name.
            figsize (Tuple[int, int], optional): Figure size. If None, uses default.
            
        Returns:
            Dict: Dictionary with plot information and base64-encoded image.
        """
        if df.empty or column not in df.columns:
            return {'error': f"Column {column} not found or DataFrame is empty"}
        
        try:
            # Get value counts
            if max_categories is None:
                max_categories = self.config['max_categories_bar']
                
            value_counts = df[column].value_counts().head(max_categories)
            
            # Create figure
            fig, ax = plt.subplots(figsize=figsize or self.config['default_figsize'])
            
            # Plot bar chart
            sns.barplot(x=value_counts.index, y=value_counts.values, ax=ax)
            
            # Set title and labels
            ax.set_title(title or f"Frequency of {column}")
            ax.set_xlabel(column)
            ax.set_ylabel("Count")
            
            # Rotate x-axis labels if there are many categories
            if len(value_counts) > 5:
                plt.xticks(rotation=45, ha='right')
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Tight layout
            fig.tight_layout()
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"bar_chart_{column}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            # Return plot information
            result = {
                'type': 'bar_chart',
                'column': column,
                'categories': len(value_counts),
                'title': title or f"Frequency of {column}",
                'image_base64': img_base64
            }
            
            if plot_path:
                result['file_path'] = plot_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating bar chart for {column}: {e}")
            return {'error': str(e)}
    
    def plot_pie_chart(self, df: pd.DataFrame, column: str,
                      max_categories: int = None,
                      title: Optional[str] = None,
                      figsize: Optional[Tuple[int, int]] = None) -> Dict:
        """
        Create a pie chart for a categorical column.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze.
            column (str): Column to plot.
            max_categories (int, optional): Maximum number of categories to include.
            title (str, optional): Plot title. If None, uses column name.
            figsize (Tuple[int, int], optional): Figure size. If None, uses default.
            
        Returns:
            Dict: Dictionary with plot information and base64-encoded image.
        """
        if df.empty or column not in df.columns:
            return {'error': f"Column {column} not found or DataFrame is empty"}
        
        try:
            # Get value counts
            if max_categories is None:
                max_categories = self.config['max_categories_pie']
                
            value_counts = df[column].value_counts()
            
            # If there are more categories than max_categories, group the rest as "Other"
            if len(value_counts) > max_categories:
                top_categories = value_counts.head(max_categories - 1)
                other_count = value_counts.iloc[max_categories - 1:].sum()
                
                # Create a new Series with top categories and "Other"
                value_counts = pd.concat([top_categories, pd.Series({'Other': other_count})])
            
            # Create figure
            fig, ax = plt.subplots(figsize=figsize or self.config['default_figsize'])
            
            # Plot pie chart
            ax.pie(value_counts.values, labels=value_counts.index, autopct='%1.1f%%',
                  shadow=True, startangle=90)
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            
            # Set title
            ax.set_title(title or f"Distribution of {column}")
            
            # Tight layout
            fig.tight_layout()
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"pie_chart_{column}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            # Return plot information
            result = {
                'type': 'pie_chart',
                'column': column,
                'categories': len(value_counts),
                'title': title or f"Distribution of {column}",
                'image_base64': img_base64
            }
            
            if plot_path:
                result['file_path'] = plot_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating pie chart for {column}: {e}")
            return {'error': str(e)}
    
    def plot_time_series(self, df: pd.DataFrame, date_column: str, value_column: str,
                        freq: str = 'D', agg_func: str = 'mean',
                        title: Optional[str] = None,
                        figsize: Optional[Tuple[int, int]] = None) -> Dict:
        """
        Create a time series plot.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze.
            date_column (str): Column with dates.
            value_column (str): Column with values to plot.
            freq (str): Frequency for resampling ('D' for daily, 'W' for weekly, etc.).
            agg_func (str): Aggregation function ('mean', 'sum', 'count', etc.).
            title (str, optional): Plot title. If None, generates based on columns.
            figsize (Tuple[int, int], optional): Figure size. If None, uses default.
            
        Returns:
            Dict: Dictionary with plot information and base64-encoded image.
        """
        if df.empty or date_column not in df.columns or value_column not in df.columns:
            return {'error': f"Columns not found or DataFrame is empty"}
        
        try:
            # Ensure date column is datetime
            if not pd.api.types.is_datetime64_dtype(df[date_column]):
                df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
            
            # Ensure value column is numeric
            if not pd.api.types.is_numeric_dtype(df[value_column]):
                try:
                    df[value_column] = pd.to_numeric(df[value_column], errors='coerce')
                except:
                    return {'error': f"Column {value_column} cannot be converted to numeric"}
            
            # Create a copy with only the relevant columns, dropping NAs
            ts_df = df[[date_column, value_column]].dropna()
            
            # Set date as index
            ts_df = ts_df.set_index(date_column)
            
            # Resample and aggregate
            if agg_func == 'mean':
                ts_resampled = ts_df.resample(freq)[value_column].mean()
            elif agg_func == 'sum':
                ts_resampled = ts_df.resample(freq)[value_column].sum()
            elif agg_func == 'count':
                ts_resampled = ts_df.resample(freq)[value_column].count()
            else:
                ts_resampled = ts_df.resample(freq)[value_column].agg(agg_func)
            
            # Create figure
            fig, ax = plt.subplots(figsize=figsize or self.config['default_figsize'])
            
            # Plot time series
            ts_resampled.plot(ax=ax)
            
            # Set title and labels
            ax.set_title(title or f"{agg_func.capitalize()} of {value_column} over time")
            ax.set_xlabel("Date")
            ax.set_ylabel(f"{agg_func.capitalize()} of {value_column}")
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Tight layout
            fig.tight_layout()
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"time_series_{value_column}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            # Return plot information
            result = {
                'type': 'time_series',
                'date_column': date_column,
                'value_column': value_column,
                'frequency': freq,
                'aggregation': agg_func,
                'title': title or f"{agg_func.capitalize()} of {value_column} over time",
                'image_base64': img_base64
            }
            
            if plot_path:
                result['file_path'] = plot_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating time series plot: {e}")
            return {'error': str(e)}
    
    def plot_scatter(self, df: pd.DataFrame, x_column: str, y_column: str,
                    hue_column: Optional[str] = None,
                    title: Optional[str] = None,
                    figsize: Optional[Tuple[int, int]] = None) -> Dict:
        """
        Create a scatter plot.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze.
            x_column (str): Column for x-axis.
            y_column (str): Column for y-axis.
            hue_column (str, optional): Column for color coding points.
            title (str, optional): Plot title. If None, generates based on columns.
            figsize (Tuple[int, int], optional): Figure size. If None, uses default.
            
        Returns:
            Dict: Dictionary with plot information and base64-encoded image.
        """
        if df.empty or x_column not in df.columns or y_column not in df.columns:
            return {'error': f"Columns not found or DataFrame is empty"}
        
        if hue_column and hue_column not in df.columns:
            return {'error': f"Hue column {hue_column} not found"}
        
        try:
            # Ensure columns are numeric
            for col in [x_column, y_column]:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    try:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    except:
                        return {'error': f"Column {col} cannot be converted to numeric"}
            
            # Create figure
            fig, ax = plt.subplots(figsize=figsize or self.config['default_figsize'])
            
            # Plot scatter
            if hue_column:
                sns.scatterplot(x=x_column, y=y_column, hue=hue_column, data=df, ax=ax)
            else:
                sns.scatterplot(x=x_column, y=y_column, data=df, ax=ax)
            
            # Set title and labels
            ax.set_title(title or f"Scatter plot of {y_column} vs {x_column}")
            ax.set_xlabel(x_column)
            ax.set_ylabel(y_column)
            
            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Tight layout
            fig.tight_layout()
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"scatter_{x_column}_{y_column}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            # Return plot information
            result = {
                'type': 'scatter',
                'x_column': x_column,
                'y_column': y_column,
                'hue_column': hue_column,
                'title': title or f"Scatter plot of {y_column} vs {x_column}",
                'image_base64': img_base64
            }
            
            if plot_path:
                result['file_path'] = plot_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating scatter plot: {e}")
            return {'error': str(e)}
    
    def generate_descriptive_analysis(self, df: pd.DataFrame, 
                                    numeric_columns: Optional[List[str]] = None,
                                    categorical_columns: Optional[List[str]] = None,
                                    date_columns: Optional[List[str]] = None,
                                    value_columns: Optional[List[str]] = None,
                                    options: Optional[Dict] = None) -> Dict:
        """
        Generate a comprehensive descriptive analysis of the data.
        
        Args:
            df (pd.DataFrame): DataFrame to analyze.
            numeric_columns (List[str], optional): List of numeric columns to analyze.
            categorical_columns (List[str], optional): List of categorical columns to analyze.
            date_columns (List[str], optional): List of date columns for time series analysis.
            value_columns (List[str], optional): List of value columns for time series analysis.
            options (Dict, optional): Additional options for analysis.
            
        Returns:
            Dict: Dictionary with analysis results.
        """
        if df.empty:
            return {
                'status': 'error',
                'message': 'Empty DataFrame',
                'timestamp': datetime.now().isoformat()
            }
        
        # Initialize results
        results = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'data_shape': {
                'rows': len(df),
                'columns': len(df.columns)
            },
            'summary_statistics': {},
            'frequency_tables': {},
            'visualizations': []
        }
        
        # Merge options with defaults
        opts = {
            'include_summary_stats': True,
            'include_frequency_tables': True,
            'include_histograms': True,
            'include_boxplots': True,
            'include_bar_charts': True,
            'include_pie_charts': True,
            'include_time_series': True,
            'include_scatter_plots': False,
            'max_categories_pie': self.config['max_categories_pie'],
            'max_categories_bar': self.config['max_categories_bar']
        }
        
        if options:
            opts.update(options)
        
        try:
            # Identify column types if not provided
            if numeric_columns is None:
                numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
            
            if categorical_columns is None:
                categorical_columns = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
            
            if date_columns is None:
                date_columns = df.select_dtypes(include=['datetime']).columns.tolist()
                # Try to identify date columns by name
                for col in df.columns:
                    if col.endswith('_date') or '_date_' in col or 'date' in col.lower():
                        if col not in date_columns:
                            try:
                                df[col] = pd.to_datetime(df[col], errors='coerce')
                                if not df[col].isna().all():
                                    date_columns.append(col)
                            except:
                                pass
            
            # Calculate summary statistics
            if opts['include_summary_stats']:
                results['summary_statistics'] = self.calculate_summary_stats(df)
            
            # Generate frequency tables
            if opts['include_frequency_tables']:
                results['frequency_tables'] = self.generate_frequency_tables(
                    df, categorical_columns, opts['max_categories_bar']
                )
            
            # Generate visualizations
            visualizations = []
            
            # Histograms for numeric columns
            if opts['include_histograms']:
                for col in numeric_columns:
                    if col.startswith('_'):  # Skip metadata columns
                        continue
                    viz = self.plot_histogram(df, col)
                    if 'error' not in viz:
                        visualizations.append(viz)
            
            # Boxplots for numeric columns
            if opts['include_boxplots']:
                for col in numeric_columns:
                    if col.startswith('_'):  # Skip metadata columns
                        continue
                    viz = self.plot_boxplot(df, col)
                    if 'error' not in viz:
                        visualizations.append(viz)
            
            # Bar charts for categorical columns
            if opts['include_bar_charts']:
                for col in categorical_columns:
                    if col.startswith('_'):  # Skip metadata columns
                        continue
                    viz = self.plot_bar_chart(df, col, opts['max_categories_bar'])
                    if 'error' not in viz:
                        visualizations.append(viz)
            
            # Pie charts for categorical columns with few categories
            if opts['include_pie_charts']:
                for col in categorical_columns:
                    if col.startswith('_'):  # Skip metadata columns
                        continue
                    if df[col].nunique() <= opts['max_categories_pie']:
                        viz = self.plot_pie_chart(df, col)
                        if 'error' not in viz:
                            visualizations.append(viz)
            
            # Time series plots
            if opts['include_time_series'] and date_columns:
                # If value_columns not specified, use numeric columns
                if value_columns is None:
                    value_columns = numeric_columns
                
                for date_col in date_columns:
                    for val_col in value_columns:
                        if val_col.startswith('_'):  # Skip metadata columns
                            continue
                        viz = self.plot_time_series(df, date_col, val_col)
                        if 'error' not in viz:
                            visualizations.append(viz)
            
            # Scatter plots
            if opts['include_scatter_plots'] and len(numeric_columns) >= 2:
                # Generate scatter plots for pairs of numeric columns
                # Limit to a reasonable number to avoid too many plots
                max_pairs = 5
                pairs = []
                
                for i, col1 in enumerate(numeric_columns):
                    if col1.startswith('_'):  # Skip metadata columns
                        continue
                    for col2 in numeric_columns[i+1:]:
                        if col2.startswith('_'):  # Skip metadata columns
                            continue
                        pairs.append((col1, col2))
                        if len(pairs) >= max_pairs:
                            break
                    if len(pairs) >= max_pairs:
                        break
                
                for x_col, y_col in pairs:
                    viz = self.plot_scatter(df, x_col, y_col)
                    if 'error' not in viz:
                        visualizations.append(viz)
            
            results['visualizations'] = visualizations
            
            return results
            
        except Exception as e:
            logger.error(f"Error generating descriptive analysis: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def analyze_project_data(self, project_id: str, form_id: Optional[str] = None,
                           filters: Optional[Dict] = None, options: Optional[Dict] = None,
                           use_cleaned: bool = True) -> Dict:
        """
        Analyze data for a specific project and form.
        
        Args:
            project_id (str): Project ID.
            form_id (str, optional): Form ID.
            filters (Dict, optional): Additional filters.
            options (Dict, optional): Analysis options.
            use_cleaned (bool): Whether to use cleaned data.
            
        Returns:
            Dict: Analysis results.
        """
        try:
            # Fetch data
            df = self.fetch_data(project_id, form_id, filters, use_cleaned)
            
            if df.empty:
                return {
                    'status': 'error',
                    'message': 'No data found',
                    'project_id': project_id,
                    'form_id': form_id,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Generate descriptive analysis
            analysis_results = self.generate_descriptive_analysis(df, options=options)
            
            # Add metadata
            analysis_results['project_id'] = project_id
            analysis_results['form_id'] = form_id
            analysis_results['filters'] = filters
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error analyzing project data: {e}")
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
    agent = DescriptiveAnalyticsAgent()
    
    # Example analysis
    result = agent.analyze_project_data(
        project_id="sample_project",
        form_id="sample_form"
    )
    
    print(json.dumps(result, indent=2))

