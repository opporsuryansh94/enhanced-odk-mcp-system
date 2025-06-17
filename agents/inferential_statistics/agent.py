#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Inferential Statistics Agent for ODK MCP System

This agent is responsible for performing inferential statistical analysis on cleaned data.
It conducts hypothesis tests, correlation analyses, and regression modeling to draw
conclusions and make predictions based on data collected through ODK forms.

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
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InferentialStatisticsAgent:
    """
    Agent for performing inferential statistical analysis on ODK form data.
    
    This agent connects to the Data Aggregation MCP or uses cleaned data from
    the Data Cleaning Agent to perform statistical tests, correlation analyses,
    and regression modeling.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the Inferential Statistics Agent.
        
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
            'output_dir': 'output/inferential_statistics',
            'save_plots': True,
            'show_plots': False,
            'alpha': 0.05,  # Default significance level
            'test_size': 0.2,  # Default test size for train/test split
            'random_state': 42  # Default random state for reproducibility
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
    
    def perform_t_test(self, df: pd.DataFrame, variable: str, 
                      group_variable: Optional[str] = None, 
                      equal_var: bool = True) -> Dict:
        """
        Perform t-test (one-sample, independent two-sample, or paired).
        
        Args:
            df (pd.DataFrame): DataFrame with data.
            variable (str): Variable to test.
            group_variable (str, optional): Grouping variable for two-sample test.
            equal_var (bool): Whether to assume equal variances for two-sample test.
            
        Returns:
            Dict: T-test results.
        """
        if df.empty or variable not in df.columns:
            return {'error': f"Variable {variable} not found or DataFrame is empty"}
        
        try:
            result = {
                'test_type': 'one_sample_t_test',
                'variable': variable,
                'alpha': self.config['alpha']
            }
            
            # One-sample t-test (against population mean of 0)
            if group_variable is None:
                data = df[variable].dropna()
                t_stat, p_value = stats.ttest_1samp(data, 0)
                
                result.update({
                    'test_type': 'one_sample_t_test',
                    'null_hypothesis': 'Population mean equals 0',
                    'alternative_hypothesis': 'Population mean does not equal 0',
                    't_statistic': float(t_stat),
                    'p_value': float(p_value),
                    'degrees_of_freedom': len(data) - 1,
                    'sample_mean': float(data.mean()),
                    'sample_size': len(data),
                    'significant': p_value < self.config['alpha']
                })
            
            # Two-sample t-test
            else:
                if group_variable not in df.columns:
                    return {'error': f"Group variable {group_variable} not found"}
                
                # Get unique groups
                groups = df[group_variable].dropna().unique()
                
                if len(groups) != 2:
                    return {'error': f"Group variable must have exactly 2 unique values for t-test, found {len(groups)}"}
                
                # Extract data for each group
                group1_data = df[df[group_variable] == groups[0]][variable].dropna()
                group2_data = df[df[group_variable] == groups[1]][variable].dropna()
                
                # Perform t-test
                t_stat, p_value = stats.ttest_ind(group1_data, group2_data, equal_var=equal_var)
                
                result.update({
                    'test_type': 'independent_two_sample_t_test',
                    'group_variable': group_variable,
                    'groups': [str(groups[0]), str(groups[1])],
                    'null_hypothesis': f'Mean of {variable} is equal between groups',
                    'alternative_hypothesis': f'Mean of {variable} is different between groups',
                    't_statistic': float(t_stat),
                    'p_value': float(p_value),
                    'equal_variances_assumed': equal_var,
                    'group1_mean': float(group1_data.mean()),
                    'group2_mean': float(group2_data.mean()),
                    'group1_size': len(group1_data),
                    'group2_size': len(group2_data),
                    'significant': p_value < self.config['alpha']
                })
                
                # Create visualization
                fig, ax = plt.subplots(figsize=self.config['default_figsize'])
                
                # Box plot
                sns.boxplot(x=group_variable, y=variable, data=df, ax=ax)
                
                # Add title and labels
                ax.set_title(f"Comparison of {variable} by {group_variable}")
                ax.set_xlabel(group_variable)
                ax.set_ylabel(variable)
                
                # Add p-value annotation
                p_text = f"p = {p_value:.4f}"
                if p_value < self.config['alpha']:
                    p_text += " (significant)"
                ax.annotate(p_text, xy=(0.5, 0.95), xycoords='axes fraction', 
                           ha='center', va='center', fontsize=12, 
                           bbox=dict(boxstyle='round', fc='white', alpha=0.8))
                
                # Save plot if configured
                plot_path = None
                if self.config['save_plots']:
                    os.makedirs(self.config['output_dir'], exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    plot_path = os.path.join(
                        self.config['output_dir'], 
                        f"ttest_{variable}_{group_variable}_{timestamp}.png"
                    )
                    fig.savefig(plot_path, dpi=self.config['default_dpi'])
                
                # Convert plot to base64 for embedding in reports
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                
                # Close figure to free memory
                plt.close(fig)
                
                result['visualization'] = {
                    'type': 'boxplot',
                    'image_base64': img_base64
                }
                
                if plot_path:
                    result['visualization']['file_path'] = plot_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing t-test: {e}")
            return {'error': str(e)}
    
    def perform_anova(self, df: pd.DataFrame, variable: str, 
                     group_variable: str) -> Dict:
        """
        Perform one-way ANOVA.
        
        Args:
            df (pd.DataFrame): DataFrame with data.
            variable (str): Dependent variable.
            group_variable (str): Grouping variable.
            
        Returns:
            Dict: ANOVA results.
        """
        if df.empty or variable not in df.columns or group_variable not in df.columns:
            return {'error': f"Variables not found or DataFrame is empty"}
        
        try:
            # Get groups
            groups = df[group_variable].dropna().unique()
            
            if len(groups) < 3:
                return {'error': f"ANOVA requires at least 3 groups, found {len(groups)}"}
            
            # Prepare data for ANOVA
            group_data = []
            group_sizes = []
            group_means = []
            
            for group in groups:
                group_values = df[df[group_variable] == group][variable].dropna()
                group_data.append(group_values)
                group_sizes.append(len(group_values))
                group_means.append(float(group_values.mean()))
            
            # Perform ANOVA
            f_stat, p_value = stats.f_oneway(*group_data)
            
            # Create result dictionary
            result = {
                'test_type': 'one_way_anova',
                'variable': variable,
                'group_variable': group_variable,
                'groups': [str(g) for g in groups],
                'null_hypothesis': f'Means of {variable} are equal across all groups',
                'alternative_hypothesis': f'At least one group mean is different',
                'f_statistic': float(f_stat),
                'p_value': float(p_value),
                'alpha': self.config['alpha'],
                'significant': p_value < self.config['alpha'],
                'group_sizes': group_sizes,
                'group_means': group_means
            }
            
            # If significant, perform post-hoc Tukey HSD test
            if p_value < self.config['alpha']:
                # Prepare data for Tukey's test
                data_for_tukey = []
                groups_for_tukey = []
                
                for i, group in enumerate(groups):
                    group_values = df[df[group_variable] == group][variable].dropna()
                    data_for_tukey.extend(group_values)
                    groups_for_tukey.extend([str(group)] * len(group_values))
                
                # Perform Tukey's test
                tukey_result = pairwise_tukeyhsd(
                    data_for_tukey, groups_for_tukey, alpha=self.config['alpha']
                )
                
                # Extract pairwise comparisons
                pairwise_comparisons = []
                for i, (group1, group2, reject, _, _, _) in enumerate(zip(
                    tukey_result.groupsunique[tukey_result.pairindices[:,0]],
                    tukey_result.groupsunique[tukey_result.pairindices[:,1]],
                    tukey_result.reject,
                    tukey_result.meandiffs,
                    tukey_result.confint[:,0],
                    tukey_result.confint[:,1]
                )):
                    pairwise_comparisons.append({
                        'group1': str(group1),
                        'group2': str(group2),
                        'mean_difference': float(tukey_result.meandiffs[i]),
                        'lower_ci': float(tukey_result.confint[i,0]),
                        'upper_ci': float(tukey_result.confint[i,1]),
                        'significant': bool(reject)
                    })
                
                result['post_hoc'] = {
                    'method': 'tukey_hsd',
                    'comparisons': pairwise_comparisons
                }
            
            # Create visualization
            fig, ax = plt.subplots(figsize=self.config['default_figsize'])
            
            # Box plot
            sns.boxplot(x=group_variable, y=variable, data=df, ax=ax)
            
            # Add title and labels
            ax.set_title(f"Comparison of {variable} by {group_variable}")
            ax.set_xlabel(group_variable)
            ax.set_ylabel(variable)
            
            # Add p-value annotation
            p_text = f"ANOVA: p = {p_value:.4f}"
            if p_value < self.config['alpha']:
                p_text += " (significant)"
            ax.annotate(p_text, xy=(0.5, 0.95), xycoords='axes fraction', 
                       ha='center', va='center', fontsize=12, 
                       bbox=dict(boxstyle='round', fc='white', alpha=0.8))
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"anova_{variable}_{group_variable}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            result['visualization'] = {
                'type': 'boxplot',
                'image_base64': img_base64
            }
            
            if plot_path:
                result['visualization']['file_path'] = plot_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing ANOVA: {e}")
            return {'error': str(e)}
    
    def calculate_correlation(self, df: pd.DataFrame, 
                            variables: Optional[List[str]] = None,
                            method: str = 'pearson') -> Dict:
        """
        Calculate correlation matrix.
        
        Args:
            df (pd.DataFrame): DataFrame with data.
            variables (List[str], optional): Variables to include. If None, uses all numeric columns.
            method (str): Correlation method ('pearson', 'spearman', or 'kendall').
            
        Returns:
            Dict: Correlation results.
        """
        if df.empty:
            return {'error': "DataFrame is empty"}
        
        try:
            # Select variables
            if variables:
                # Check if all variables exist
                missing_vars = [var for var in variables if var not in df.columns]
                if missing_vars:
                    return {'error': f"Variables not found: {', '.join(missing_vars)}"}
                
                # Select only numeric variables
                numeric_vars = [var for var in variables if pd.api.types.is_numeric_dtype(df[var])]
                if not numeric_vars:
                    return {'error': "No numeric variables found in the specified list"}
                
                selected_df = df[numeric_vars]
            else:
                # Select all numeric columns
                selected_df = df.select_dtypes(include=['number'])
                
                # Remove metadata columns
                selected_df = selected_df[[col for col in selected_df.columns if not col.startswith('_')]]
                
                if selected_df.empty:
                    return {'error': "No numeric columns found in the DataFrame"}
            
            # Calculate correlation matrix
            if method == 'pearson':
                corr_matrix = selected_df.corr(method='pearson')
            elif method == 'spearman':
                corr_matrix = selected_df.corr(method='spearman')
            elif method == 'kendall':
                corr_matrix = selected_df.corr(method='kendall')
            else:
                return {'error': f"Invalid correlation method: {method}"}
            
            # Calculate p-values for Pearson correlation
            p_values = None
            if method == 'pearson':
                p_values = pd.DataFrame(np.zeros_like(corr_matrix), 
                                      index=corr_matrix.index, 
                                      columns=corr_matrix.columns)
                
                for i, var1 in enumerate(corr_matrix.columns):
                    for j, var2 in enumerate(corr_matrix.columns):
                        if i == j:
                            p_values.loc[var1, var2] = 0.0
                        else:
                            _, p = stats.pearsonr(
                                selected_df[var1].dropna(),
                                selected_df[var2].dropna()
                            )
                            p_values.loc[var1, var2] = p
            
            # Create visualization
            fig, ax = plt.subplots(figsize=self.config['default_figsize'])
            
            # Heatmap
            mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
            sns.heatmap(corr_matrix, mask=mask, annot=True, fmt=".2f", cmap='coolwarm',
                       vmin=-1, vmax=1, center=0, square=True, linewidths=.5, ax=ax)
            
            # Add title
            ax.set_title(f"{method.capitalize()} Correlation Matrix")
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"correlation_{method}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            # Create result dictionary
            result = {
                'method': method,
                'variables': list(corr_matrix.columns),
                'correlation_matrix': corr_matrix.to_dict(),
                'visualization': {
                    'type': 'heatmap',
                    'image_base64': img_base64
                }
            }
            
            if p_values is not None:
                result['p_values'] = p_values.to_dict()
            
            if plot_path:
                result['visualization']['file_path'] = plot_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return {'error': str(e)}
    
    def run_linear_regression(self, df: pd.DataFrame, 
                            dependent_variable: str,
                            independent_variables: List[str],
                            include_categorical: bool = False) -> Dict:
        """
        Run linear regression analysis.
        
        Args:
            df (pd.DataFrame): DataFrame with data.
            dependent_variable (str): Dependent variable.
            independent_variables (List[str]): Independent variables.
            include_categorical (bool): Whether to include categorical variables as dummies.
            
        Returns:
            Dict: Regression results.
        """
        if df.empty:
            return {'error': "DataFrame is empty"}
        
        if dependent_variable not in df.columns:
            return {'error': f"Dependent variable {dependent_variable} not found"}
        
        missing_vars = [var for var in independent_variables if var not in df.columns]
        if missing_vars:
            return {'error': f"Independent variables not found: {', '.join(missing_vars)}"}
        
        try:
            # Prepare data
            y = df[dependent_variable].dropna()
            
            # Select independent variables
            X_df = df[independent_variables].copy()
            
            # Handle categorical variables if requested
            if include_categorical:
                # Identify categorical columns
                cat_columns = X_df.select_dtypes(include=['object', 'category']).columns
                
                # Create dummy variables
                if not cat_columns.empty:
                    X_df = pd.get_dummies(X_df, columns=cat_columns, drop_first=True)
            else:
                # Keep only numeric columns
                X_df = X_df.select_dtypes(include=['number'])
            
            # Drop rows with missing values
            valid_rows = ~X_df.isna().any(axis=1) & ~y.isna()
            X = X_df[valid_rows]
            y = y[valid_rows]
            
            if len(X) < len(independent_variables) + 1:
                return {'error': "Not enough data points for regression"}
            
            # Add constant for intercept
            X_with_const = sm.add_constant(X)
            
            # Fit OLS model
            model = sm.OLS(y, X_with_const)
            results = model.fit()
            
            # Extract results
            coefficients = results.params.to_dict()
            p_values = results.pvalues.to_dict()
            conf_int = results.conf_int()
            conf_intervals = {
                var: [float(conf_int.loc[var, 0]), float(conf_int.loc[var, 1])]
                for var in coefficients.keys()
            }
            
            # Calculate metrics
            r_squared = results.rsquared
            adj_r_squared = results.rsquared_adj
            f_statistic = results.fvalue
            f_pvalue = results.f_pvalue
            aic = results.aic
            bic = results.bic
            
            # Create visualization for actual vs predicted
            fig, ax = plt.subplots(figsize=self.config['default_figsize'])
            
            # Scatter plot of actual vs predicted
            predicted = results.predict(X_with_const)
            ax.scatter(y, predicted, alpha=0.5)
            
            # Add diagonal line (perfect prediction)
            min_val = min(y.min(), predicted.min())
            max_val = max(y.max(), predicted.max())
            ax.plot([min_val, max_val], [min_val, max_val], 'r--')
            
            # Add title and labels
            ax.set_title(f"Actual vs Predicted: {dependent_variable}")
            ax.set_xlabel("Actual Values")
            ax.set_ylabel("Predicted Values")
            
            # Add R² annotation
            ax.annotate(f"R² = {r_squared:.4f}", xy=(0.05, 0.95), xycoords='axes fraction', 
                       ha='left', va='center', fontsize=12, 
                       bbox=dict(boxstyle='round', fc='white', alpha=0.8))
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"regression_{dependent_variable}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            # Create result dictionary
            result = {
                'model_type': 'linear_regression',
                'dependent_variable': dependent_variable,
                'independent_variables': independent_variables,
                'sample_size': len(y),
                'coefficients': coefficients,
                'p_values': p_values,
                'confidence_intervals': conf_intervals,
                'r_squared': float(r_squared),
                'adjusted_r_squared': float(adj_r_squared),
                'f_statistic': float(f_statistic),
                'f_pvalue': float(f_pvalue),
                'aic': float(aic),
                'bic': float(bic),
                'significant_predictors': [
                    var for var, p in p_values.items() 
                    if p < self.config['alpha'] and var != 'const'
                ],
                'model_significant': f_pvalue < self.config['alpha'],
                'visualization': {
                    'type': 'actual_vs_predicted',
                    'image_base64': img_base64
                }
            }
            
            if plot_path:
                result['visualization']['file_path'] = plot_path
            
            # Add summary text
            summary_text = f"Linear regression model for {dependent_variable}:\n"
            summary_text += f"- R² = {r_squared:.4f}, Adjusted R² = {adj_r_squared:.4f}\n"
            summary_text += f"- F-statistic = {f_statistic:.4f}, p-value = {f_pvalue:.4f}\n"
            summary_text += f"- Sample size = {len(y)}\n\n"
            
            summary_text += "Coefficients:\n"
            for var, coef in coefficients.items():
                p = p_values[var]
                ci = conf_intervals[var]
                stars = ''
                if p < 0.001:
                    stars = '***'
                elif p < 0.01:
                    stars = '**'
                elif p < 0.05:
                    stars = '*'
                
                summary_text += f"- {var}: {coef:.4f} ({ci[0]:.4f}, {ci[1]:.4f}) {stars}\n"
            
            summary_text += "\nSignificance codes: *** p<0.001, ** p<0.01, * p<0.05"
            
            result['summary'] = summary_text
            
            return result
            
        except Exception as e:
            logger.error(f"Error running linear regression: {e}")
            return {'error': str(e)}
    
    def run_logistic_regression(self, df: pd.DataFrame, 
                              dependent_variable: str,
                              independent_variables: List[str],
                              include_categorical: bool = False) -> Dict:
        """
        Run logistic regression analysis.
        
        Args:
            df (pd.DataFrame): DataFrame with data.
            dependent_variable (str): Binary dependent variable.
            independent_variables (List[str]): Independent variables.
            include_categorical (bool): Whether to include categorical variables as dummies.
            
        Returns:
            Dict: Regression results.
        """
        if df.empty:
            return {'error': "DataFrame is empty"}
        
        if dependent_variable not in df.columns:
            return {'error': f"Dependent variable {dependent_variable} not found"}
        
        missing_vars = [var for var in independent_variables if var not in df.columns]
        if missing_vars:
            return {'error': f"Independent variables not found: {', '.join(missing_vars)}"}
        
        try:
            # Check if dependent variable is binary
            unique_values = df[dependent_variable].dropna().unique()
            if len(unique_values) != 2:
                return {'error': f"Dependent variable must be binary, found {len(unique_values)} unique values"}
            
            # Prepare data
            y = df[dependent_variable].dropna()
            
            # Select independent variables
            X_df = df[independent_variables].copy()
            
            # Handle categorical variables if requested
            if include_categorical:
                # Identify categorical columns
                cat_columns = X_df.select_dtypes(include=['object', 'category']).columns
                
                # Create dummy variables
                if not cat_columns.empty:
                    X_df = pd.get_dummies(X_df, columns=cat_columns, drop_first=True)
            else:
                # Keep only numeric columns
                X_df = X_df.select_dtypes(include=['number'])
            
            # Drop rows with missing values
            valid_rows = ~X_df.isna().any(axis=1) & ~y.isna()
            X = X_df[valid_rows]
            y = y[valid_rows]
            
            if len(X) < len(independent_variables) + 1:
                return {'error': "Not enough data points for regression"}
            
            # Split data for evaluation
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config['test_size'], 
                random_state=self.config['random_state']
            )
            
            # Fit logistic regression model using sklearn
            model = LogisticRegression(random_state=self.config['random_state'])
            model.fit(X_train, y_train)
            
            # Make predictions
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            
            # Get coefficients
            coefficients = {
                'intercept': float(model.intercept_[0])
            }
            for i, var in enumerate(X.columns):
                coefficients[var] = float(model.coef_[0, i])
            
            # Calculate odds ratios
            odds_ratios = {
                var: np.exp(coef) for var, coef in coefficients.items()
                if var != 'intercept'
            }
            
            # Create visualization for ROC curve
            fig, ax = plt.subplots(figsize=self.config['default_figsize'])
            
            # Calculate ROC curve
            fpr, tpr, _ = metrics.roc_curve(y_test, y_pred_proba)
            roc_auc = metrics.auc(fpr, tpr)
            
            # Plot ROC curve
            ax.plot(fpr, tpr, label=f'ROC curve (AUC = {roc_auc:.2f})')
            ax.plot([0, 1], [0, 1], 'k--')  # Diagonal line
            
            # Add title and labels
            ax.set_title(f"ROC Curve: {dependent_variable}")
            ax.set_xlabel("False Positive Rate")
            ax.set_ylabel("True Positive Rate")
            ax.legend(loc="lower right")
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"logistic_regression_{dependent_variable}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            # Create result dictionary
            result = {
                'model_type': 'logistic_regression',
                'dependent_variable': dependent_variable,
                'independent_variables': independent_variables,
                'sample_size': len(y),
                'train_size': len(y_train),
                'test_size': len(y_test),
                'coefficients': coefficients,
                'odds_ratios': odds_ratios,
                'metrics': {
                    'accuracy': float(accuracy),
                    'precision': float(precision),
                    'recall': float(recall),
                    'f1_score': float(f1),
                    'roc_auc': float(roc_auc)
                },
                'visualization': {
                    'type': 'roc_curve',
                    'image_base64': img_base64
                }
            }
            
            if plot_path:
                result['visualization']['file_path'] = plot_path
            
            # Add summary text
            summary_text = f"Logistic regression model for {dependent_variable}:\n"
            summary_text += f"- Accuracy = {accuracy:.4f}\n"
            summary_text += f"- Precision = {precision:.4f}\n"
            summary_text += f"- Recall = {recall:.4f}\n"
            summary_text += f"- F1 Score = {f1:.4f}\n"
            summary_text += f"- ROC AUC = {roc_auc:.4f}\n"
            summary_text += f"- Sample size = {len(y)}\n\n"
            
            summary_text += "Coefficients and Odds Ratios:\n"
            summary_text += f"- Intercept: {coefficients['intercept']:.4f}\n"
            
            for var in X.columns:
                coef = coefficients[var]
                odds = odds_ratios[var]
                summary_text += f"- {var}: {coef:.4f} (Odds Ratio: {odds:.4f})\n"
            
            result['summary'] = summary_text
            
            return result
            
        except Exception as e:
            logger.error(f"Error running logistic regression: {e}")
            return {'error': str(e)}
    
    def perform_chi_square_test(self, df: pd.DataFrame, 
                               variable1: str, 
                               variable2: str) -> Dict:
        """
        Perform chi-square test of independence.
        
        Args:
            df (pd.DataFrame): DataFrame with data.
            variable1 (str): First categorical variable.
            variable2 (str): Second categorical variable.
            
        Returns:
            Dict: Chi-square test results.
        """
        if df.empty:
            return {'error': "DataFrame is empty"}
        
        if variable1 not in df.columns or variable2 not in df.columns:
            return {'error': f"Variables not found"}
        
        try:
            # Create contingency table
            contingency_table = pd.crosstab(df[variable1], df[variable2])
            
            # Perform chi-square test
            chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
            
            # Create visualization
            fig, ax = plt.subplots(figsize=self.config['default_figsize'])
            
            # Heatmap of contingency table
            sns.heatmap(contingency_table, annot=True, fmt='d', cmap='Blues', ax=ax)
            
            # Add title and labels
            ax.set_title(f"Contingency Table: {variable1} vs {variable2}")
            ax.set_xlabel(variable2)
            ax.set_ylabel(variable1)
            
            # Add chi-square test result
            p_text = f"Chi-square = {chi2:.2f}, p = {p_value:.4f}"
            if p_value < self.config['alpha']:
                p_text += " (significant)"
            ax.annotate(p_text, xy=(0.5, 0.01), xycoords='figure fraction', 
                       ha='center', va='bottom', fontsize=12, 
                       bbox=dict(boxstyle='round', fc='white', alpha=0.8))
            
            # Save plot if configured
            plot_path = None
            if self.config['save_plots']:
                os.makedirs(self.config['output_dir'], exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                plot_path = os.path.join(
                    self.config['output_dir'], 
                    f"chi_square_{variable1}_{variable2}_{timestamp}.png"
                )
                fig.savefig(plot_path, dpi=self.config['default_dpi'])
            
            # Convert plot to base64 for embedding in reports
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=self.config['default_dpi'])
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            
            # Close figure to free memory
            plt.close(fig)
            
            # Create result dictionary
            result = {
                'test_type': 'chi_square_test',
                'variable1': variable1,
                'variable2': variable2,
                'null_hypothesis': f'{variable1} and {variable2} are independent',
                'alternative_hypothesis': f'{variable1} and {variable2} are not independent',
                'chi_square_statistic': float(chi2),
                'p_value': float(p_value),
                'degrees_of_freedom': int(dof),
                'alpha': self.config['alpha'],
                'significant': p_value < self.config['alpha'],
                'contingency_table': contingency_table.to_dict(),
                'visualization': {
                    'type': 'heatmap',
                    'image_base64': img_base64
                }
            }
            
            if plot_path:
                result['visualization']['file_path'] = plot_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing chi-square test: {e}")
            return {'error': str(e)}
    
    def analyze_project_data(self, project_id: str, form_id: Optional[str] = None,
                           filters: Optional[Dict] = None, options: Optional[Dict] = None,
                           use_cleaned: bool = True) -> Dict:
        """
        Perform inferential statistical analysis on project data.
        
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
            
            # Merge options with defaults
            opts = {
                'correlation_method': 'pearson',
                'include_t_tests': True,
                'include_anova': True,
                'include_correlation': True,
                'include_regression': True,
                'include_chi_square': True,
                'regression_target': None,
                'regression_predictors': None,
                'categorical_variables': None,
                'numeric_variables': None,
                'group_variables': None
            }
            
            if options:
                opts.update(options)
            
            # Initialize results
            results = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'project_id': project_id,
                'form_id': form_id,
                'data_shape': {
                    'rows': len(df),
                    'columns': len(df.columns)
                },
                'analyses': []
            }
            
            # Identify column types if not provided
            numeric_variables = opts.get('numeric_variables')
            categorical_variables = opts.get('categorical_variables')
            group_variables = opts.get('group_variables')
            
            if numeric_variables is None:
                numeric_variables = df.select_dtypes(include=['number']).columns.tolist()
                # Remove metadata columns
                numeric_variables = [col for col in numeric_variables if not col.startswith('_')]
            
            if categorical_variables is None:
                categorical_variables = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
                # Remove metadata columns
                categorical_variables = [col for col in categorical_variables if not col.startswith('_')]
            
            if group_variables is None:
                # Use categorical variables with few unique values as group variables
                group_variables = [
                    col for col in categorical_variables 
                    if df[col].nunique() >= 2 and df[col].nunique() <= 10
                ]
            
            # Perform correlation analysis
            if opts['include_correlation'] and len(numeric_variables) >= 2:
                correlation_result = self.calculate_correlation(
                    df, numeric_variables, opts['correlation_method']
                )
                
                if 'error' not in correlation_result:
                    results['analyses'].append({
                        'type': 'correlation',
                        'result': correlation_result
                    })
            
            # Perform t-tests
            if opts['include_t_tests'] and len(numeric_variables) >= 1 and len(group_variables) >= 1:
                t_test_results = []
                
                # Limit to a reasonable number of tests
                max_tests = 5
                count = 0
                
                for num_var in numeric_variables:
                    for group_var in group_variables:
                        # Check if group variable has exactly 2 unique values
                        if df[group_var].nunique() == 2:
                            t_test_result = self.perform_t_test(df, num_var, group_var)
                            
                            if 'error' not in t_test_result:
                                t_test_results.append(t_test_result)
                                count += 1
                                
                                if count >= max_tests:
                                    break
                    
                    if count >= max_tests:
                        break
                
                if t_test_results:
                    results['analyses'].append({
                        'type': 't_tests',
                        'results': t_test_results
                    })
            
            # Perform ANOVA
            if opts['include_anova'] and len(numeric_variables) >= 1 and len(group_variables) >= 1:
                anova_results = []
                
                # Limit to a reasonable number of tests
                max_tests = 3
                count = 0
                
                for num_var in numeric_variables:
                    for group_var in group_variables:
                        # Check if group variable has at least 3 unique values
                        if df[group_var].nunique() >= 3:
                            anova_result = self.perform_anova(df, num_var, group_var)
                            
                            if 'error' not in anova_result:
                                anova_results.append(anova_result)
                                count += 1
                                
                                if count >= max_tests:
                                    break
                    
                    if count >= max_tests:
                        break
                
                if anova_results:
                    results['analyses'].append({
                        'type': 'anova',
                        'results': anova_results
                    })
            
            # Perform chi-square tests
            if opts['include_chi_square'] and len(categorical_variables) >= 2:
                chi_square_results = []
                
                # Limit to a reasonable number of tests
                max_tests = 3
                count = 0
                
                for i, cat_var1 in enumerate(categorical_variables):
                    for cat_var2 in categorical_variables[i+1:]:
                        chi_square_result = self.perform_chi_square_test(df, cat_var1, cat_var2)
                        
                        if 'error' not in chi_square_result:
                            chi_square_results.append(chi_square_result)
                            count += 1
                            
                            if count >= max_tests:
                                break
                    
                    if count >= max_tests:
                        break
                
                if chi_square_results:
                    results['analyses'].append({
                        'type': 'chi_square',
                        'results': chi_square_results
                    })
            
            # Perform regression analysis
            if opts['include_regression'] and len(numeric_variables) >= 2:
                regression_results = []
                
                # Use specified target and predictors if provided
                if opts['regression_target'] and opts['regression_predictors']:
                    target = opts['regression_target']
                    predictors = opts['regression_predictors']
                    
                    if target in df.columns and all(pred in df.columns for pred in predictors):
                        # Check if target is binary for logistic regression
                        if df[target].nunique() == 2:
                            logistic_result = self.run_logistic_regression(
                                df, target, predictors, include_categorical=True
                            )
                            
                            if 'error' not in logistic_result:
                                regression_results.append(logistic_result)
                        
                        # Run linear regression for numeric target
                        if pd.api.types.is_numeric_dtype(df[target]):
                            linear_result = self.run_linear_regression(
                                df, target, predictors, include_categorical=True
                            )
                            
                            if 'error' not in linear_result:
                                regression_results.append(linear_result)
                else:
                    # Auto-select target and predictors
                    # Limit to a reasonable number of models
                    max_models = 2
                    count = 0
                    
                    for target in numeric_variables:
                        # Use other numeric variables as predictors
                        predictors = [var for var in numeric_variables if var != target]
                        
                        if predictors:
                            linear_result = self.run_linear_regression(
                                df, target, predictors, include_categorical=False
                            )
                            
                            if 'error' not in linear_result:
                                regression_results.append(linear_result)
                                count += 1
                                
                                if count >= max_models:
                                    break
                
                if regression_results:
                    results['analyses'].append({
                        'type': 'regression',
                        'results': regression_results
                    })
            
            return results
            
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
    agent = InferentialStatisticsAgent()
    
    # Example analysis
    result = agent.analyze_project_data(
        project_id="sample_project",
        form_id="sample_form"
    )
    
    print(json.dumps(result, indent=2))

