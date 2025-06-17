#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data Cleaning & Preprocessing Agent for ODK MCP System

This agent is responsible for cleaning and preprocessing data collected through ODK forms.
It handles missing values, outliers, data type conversions, and other preprocessing tasks
to prepare data for analysis.

Author: ODK MCP System
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import requests
from typing import Dict, List, Union, Optional, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataCleaningAgent:
    """
    Agent for cleaning and preprocessing ODK form data.
    
    This agent connects to the Data Aggregation MCP to retrieve raw data,
    performs cleaning and preprocessing operations, and returns the cleaned data
    for further analysis.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the Data Cleaning Agent.
        
        Args:
            config_path (str, optional): Path to configuration file. If None, 
                                        uses default configuration.
        """
        self.config = self._load_config(config_path)
        self.daa_mcp_url = self.config.get('daa_mcp_url', 'http://localhost:5003/v1')
        self.auth_token = self.config.get('auth_token')
        
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
            'default_missing_values': ['', 'NA', 'N/A', 'na', 'n/a', 'null', 'NULL', 'None', 'none'],
            'outlier_detection_method': 'iqr',  # Options: 'iqr', 'zscore', 'none'
            'outlier_threshold': 1.5,  # For IQR method
            'zscore_threshold': 3.0,  # For Z-score method
            'default_dtypes': {
                'integer': 'int64',
                'decimal': 'float64',
                'text': 'string',
                'select_one': 'category',
                'select_multiple': 'string',
                'date': 'datetime64[ns]',
                'time': 'datetime64[ns]',
                'dateTime': 'datetime64[ns]',
                'geopoint': 'string',
                'geotrace': 'string',
                'geoshape': 'string',
                'binary': 'string',
                'barcode': 'string',
                'calculate': 'string'
            }
        }
        
        if not config_path:
            return default_config
        
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Merge user config with defaults
                for key, value in user_config.items():
                    if key == 'default_dtypes' and isinstance(value, dict):
                        default_config['default_dtypes'].update(value)
                    else:
                        default_config[key] = value
                return default_config
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            return default_config
    
    def fetch_data(self, project_id: str, form_id: Optional[str] = None, 
                  filters: Optional[Dict] = None) -> pd.DataFrame:
        """
        Fetch data from Data Aggregation MCP.
        
        Args:
            project_id (str): Project ID to fetch data for.
            form_id (str, optional): Form ID to filter by.
            filters (Dict, optional): Additional filters to apply.
            
        Returns:
            pd.DataFrame: DataFrame containing the fetched data.
        """
        try:
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
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            raise
    
    def get_form_schema(self, project_id: str, form_id: str) -> Dict:
        """
        Get form schema from Form Management MCP.
        
        Args:
            project_id (str): Project ID.
            form_id (str): Form ID.
            
        Returns:
            Dict: Form schema with field types and constraints.
        """
        try:
            # This would typically call the Form Management MCP
            # For now, we'll simulate with a placeholder
            # In a real implementation, this would fetch the actual form schema
            
            # Placeholder for form schema
            # In a real implementation, this would be fetched from the Form Management MCP
            form_schema = {
                'fields': {}
            }
            
            return form_schema
        except Exception as e:
            logger.error(f"Error getting form schema: {e}")
            return {'fields': {}}
    
    def clean_data(self, df: pd.DataFrame, form_schema: Optional[Dict] = None, 
                  options: Optional[Dict] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        Clean and preprocess data.
        
        Args:
            df (pd.DataFrame): DataFrame to clean.
            form_schema (Dict, optional): Form schema with field types and constraints.
            options (Dict, optional): Cleaning options to override defaults.
            
        Returns:
            Tuple[pd.DataFrame, Dict]: Cleaned DataFrame and cleaning report.
        """
        if df.empty:
            return df, {'status': 'error', 'message': 'Empty DataFrame'}
        
        # Initialize cleaning report
        report = {
            'original_rows': len(df),
            'original_columns': len(df.columns),
            'missing_values': {},
            'outliers': {},
            'type_conversions': {},
            'dropped_rows': 0,
            'imputed_values': {},
            'final_rows': 0,
            'final_columns': 0,
            'cleaning_timestamp': datetime.now().isoformat()
        }
        
        # Merge options with defaults
        opts = {
            'handle_missing': True,
            'detect_outliers': True,
            'convert_types': True,
            'drop_na_threshold': 0.5,  # Drop rows with more than 50% missing values
            'missing_values': self.config['default_missing_values'],
            'outlier_detection_method': self.config['outlier_detection_method'],
            'outlier_threshold': self.config['outlier_threshold'],
            'zscore_threshold': self.config['zscore_threshold']
        }
        
        if options:
            opts.update(options)
        
        # Step 1: Handle missing values
        if opts['handle_missing']:
            df, missing_report = self._handle_missing_values(df, opts)
            report['missing_values'] = missing_report
        
        # Step 2: Convert data types
        if opts['convert_types']:
            df, type_report = self._convert_data_types(df, form_schema)
            report['type_conversions'] = type_report
        
        # Step 3: Detect and handle outliers
        if opts['detect_outliers']:
            df, outlier_report = self._detect_outliers(df, opts)
            report['outliers'] = outlier_report
        
        # Update final stats
        report['final_rows'] = len(df)
        report['final_columns'] = len(df.columns)
        
        return df, report
    
    def _handle_missing_values(self, df: pd.DataFrame, opts: Dict) -> Tuple[pd.DataFrame, Dict]:
        """
        Handle missing values in the DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame to process.
            opts (Dict): Options for handling missing values.
            
        Returns:
            Tuple[pd.DataFrame, Dict]: Processed DataFrame and missing values report.
        """
        report = {
            'total_missing': 0,
            'missing_by_column': {},
            'dropped_rows': 0,
            'imputed_values': {}
        }
        
        # Replace custom missing values with NaN
        df = df.replace(opts['missing_values'], np.nan)
        
        # Calculate missing values by column
        missing_counts = df.isna().sum()
        total_missing = missing_counts.sum()
        
        report['total_missing'] = int(total_missing)
        
        for col in df.columns:
            missing_count = missing_counts[col]
            if missing_count > 0:
                report['missing_by_column'][col] = int(missing_count)
        
        # Drop rows with too many missing values
        if opts['drop_na_threshold'] < 1.0:
            threshold = int(len(df.columns) * opts['drop_na_threshold'])
            before_rows = len(df)
            df = df.dropna(thresh=threshold)
            dropped_rows = before_rows - len(df)
            report['dropped_rows'] = int(dropped_rows)
        
        # Basic imputation for remaining missing values
        # For numeric columns, use median
        # For categorical/text columns, use mode
        for col in df.columns:
            if df[col].isna().any():
                if pd.api.types.is_numeric_dtype(df[col]):
                    median_value = df[col].median()
                    df[col] = df[col].fillna(median_value)
                    report['imputed_values'][col] = {
                        'method': 'median',
                        'value': float(median_value) if not pd.isna(median_value) else None,
                        'count': int(missing_counts[col])
                    }
                else:
                    # Use mode for non-numeric columns
                    mode_value = df[col].mode()[0] if not df[col].mode().empty else None
                    df[col] = df[col].fillna(mode_value)
                    report['imputed_values'][col] = {
                        'method': 'mode',
                        'value': mode_value,
                        'count': int(missing_counts[col])
                    }
        
        return df, report
    
    def _convert_data_types(self, df: pd.DataFrame, form_schema: Optional[Dict] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        Convert data types based on form schema or inference.
        
        Args:
            df (pd.DataFrame): DataFrame to process.
            form_schema (Dict, optional): Form schema with field types.
            
        Returns:
            Tuple[pd.DataFrame, Dict]: Processed DataFrame and type conversion report.
        """
        report = {
            'conversions': {},
            'errors': {}
        }
        
        # If form schema is provided, use it to determine types
        if form_schema and 'fields' in form_schema:
            for field_name, field_info in form_schema['fields'].items():
                if field_name in df.columns:
                    field_type = field_info.get('type', 'text')
                    target_dtype = self.config['default_dtypes'].get(field_type, 'string')
                    
                    try:
                        # Handle special cases
                        if target_dtype == 'datetime64[ns]':
                            df[field_name] = pd.to_datetime(df[field_name], errors='coerce')
                        elif target_dtype == 'category':
                            df[field_name] = df[field_name].astype('category')
                        else:
                            df[field_name] = df[field_name].astype(target_dtype)
                        
                        report['conversions'][field_name] = {
                            'from': str(df[field_name].dtype),
                            'to': target_dtype
                        }
                    except Exception as e:
                        report['errors'][field_name] = str(e)
        else:
            # If no schema, try to infer types
            for col in df.columns:
                # Skip metadata columns
                if col.startswith('_'):
                    continue
                
                # Try to convert to numeric if possible
                try:
                    if df[col].str.contains(r'^\d+$').all():
                        # Integers
                        df[col] = df[col].astype('int64')
                        report['conversions'][col] = {
                            'from': 'object',
                            'to': 'int64'
                        }
                    elif df[col].str.contains(r'^\d+\.\d+$').all():
                        # Floats
                        df[col] = df[col].astype('float64')
                        report['conversions'][col] = {
                            'from': 'object',
                            'to': 'float64'
                        }
                    # Try to convert to datetime
                    elif df[col].str.contains(r'\d{4}-\d{2}-\d{2}').all():
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                        report['conversions'][col] = {
                            'from': 'object',
                            'to': 'datetime64[ns]'
                        }
                except (AttributeError, ValueError, TypeError) as e:
                    # If conversion fails, leave as is
                    pass
        
        return df, report
    
    def _detect_outliers(self, df: pd.DataFrame, opts: Dict) -> Tuple[pd.DataFrame, Dict]:
        """
        Detect and handle outliers in numeric columns.
        
        Args:
            df (pd.DataFrame): DataFrame to process.
            opts (Dict): Options for outlier detection.
            
        Returns:
            Tuple[pd.DataFrame, Dict]: Processed DataFrame and outlier report.
        """
        report = {
            'detected': {},
            'handled': {}
        }
        
        # Only process numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        for col in numeric_cols:
            # Skip metadata columns
            if col.startswith('_'):
                continue
                
            values = df[col].dropna()
            
            # Skip if not enough values
            if len(values) < 4:
                continue
            
            outliers = []
            
            if opts['outlier_detection_method'] == 'iqr':
                # IQR method
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - opts['outlier_threshold'] * IQR
                upper_bound = Q3 + opts['outlier_threshold'] * IQR
                
                outlier_mask = (values < lower_bound) | (values > upper_bound)
                outliers = values[outlier_mask].index.tolist()
                
                report['detected'][col] = {
                    'method': 'iqr',
                    'lower_bound': float(lower_bound),
                    'upper_bound': float(upper_bound),
                    'count': len(outliers)
                }
                
            elif opts['outlier_detection_method'] == 'zscore':
                # Z-score method
                mean = values.mean()
                std = values.std()
                
                if std > 0:  # Avoid division by zero
                    z_scores = (values - mean) / std
                    outlier_mask = abs(z_scores) > opts['zscore_threshold']
                    outliers = values[outlier_mask].index.tolist()
                    
                    report['detected'][col] = {
                        'method': 'zscore',
                        'threshold': opts['zscore_threshold'],
                        'count': len(outliers)
                    }
            
            # Handle outliers (replace with median)
            if outliers:
                median_value = values.median()
                df.loc[outliers, col] = median_value
                
                report['handled'][col] = {
                    'method': 'replace_with_median',
                    'replacement_value': float(median_value),
                    'count': len(outliers)
                }
        
        return df, report
    
    def save_cleaned_data(self, df: pd.DataFrame, project_id: str, form_id: str, 
                         output_format: str = 'csv', output_path: Optional[str] = None) -> str:
        """
        Save cleaned data to file or return as specified format.
        
        Args:
            df (pd.DataFrame): Cleaned DataFrame.
            project_id (str): Project ID.
            form_id (str): Form ID.
            output_format (str): Output format ('csv', 'json', 'excel').
            output_path (str, optional): Path to save the file. If None, uses default.
            
        Returns:
            str: Path to saved file or data string.
        """
        if df.empty:
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cleaned_data_{project_id}_{form_id}_{timestamp}"
        
        if not output_path:
            output_path = os.path.join(os.getcwd(), 'output')
            os.makedirs(output_path, exist_ok=True)
        
        full_path = ""
        
        if output_format.lower() == 'csv':
            full_path = os.path.join(output_path, f"{filename}.csv")
            df.to_csv(full_path, index=False)
        elif output_format.lower() == 'json':
            full_path = os.path.join(output_path, f"{filename}.json")
            df.to_json(full_path, orient='records')
        elif output_format.lower() == 'excel':
            full_path = os.path.join(output_path, f"{filename}.xlsx")
            df.to_excel(full_path, index=False)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        
        logger.info(f"Saved cleaned data to {full_path}")
        return full_path
    
    def process_data(self, project_id: str, form_id: Optional[str] = None, 
                    filters: Optional[Dict] = None, options: Optional[Dict] = None,
                    output_format: str = 'csv', output_path: Optional[str] = None) -> Dict:
        """
        Process data end-to-end: fetch, clean, and save.
        
        Args:
            project_id (str): Project ID.
            form_id (str, optional): Form ID.
            filters (Dict, optional): Additional filters.
            options (Dict, optional): Cleaning options.
            output_format (str): Output format.
            output_path (str, optional): Path to save output.
            
        Returns:
            Dict: Processing report.
        """
        try:
            # Fetch data
            df = self.fetch_data(project_id, form_id, filters)
            
            if df.empty:
                return {
                    'status': 'error',
                    'message': 'No data found',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Get form schema if form_id is provided
            form_schema = None
            if form_id:
                form_schema = self.get_form_schema(project_id, form_id)
            
            # Clean data
            cleaned_df, cleaning_report = self.clean_data(df, form_schema, options)
            
            # Save cleaned data
            output_file = self.save_cleaned_data(
                cleaned_df, project_id, form_id or 'all',
                output_format, output_path
            )
            
            # Prepare final report
            report = {
                'status': 'success',
                'project_id': project_id,
                'form_id': form_id,
                'filters': filters,
                'cleaning_report': cleaning_report,
                'output_file': output_file,
                'output_format': output_format,
                'timestamp': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }

# Example usage
if __name__ == "__main__":
    # This would be called by the agent framework or directly
    agent = DataCleaningAgent()
    
    # Example processing
    result = agent.process_data(
        project_id="sample_project",
        form_id="sample_form",
        output_format="csv"
    )
    
    print(json.dumps(result, indent=2))

