"""
Enhanced data insights analyzer for ODK MCP System.
Provides automatic insights, predictive analytics, and intelligent recommendations.
"""

import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union, Optional, Any
from datetime import datetime, timedelta
import pickle
from scipy import stats
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, accuracy_score

from ..config import AI_CONFIG, check_subscription_limit
from ..utils.logging import setup_logger, log_ai_event


class EnhancedDataInsightsAnalyzer:
    """
    Enhanced data insights analyzer that provides automatic insights,
    predictive analytics, and intelligent recommendations for ODK data.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the enhanced data insights analyzer.
        
        Args:
            config: Configuration dictionary. If None, uses the global AI_CONFIG.
        """
        self.config = config or AI_CONFIG["data_insights"]
        self.logger = setup_logger("enhanced_data_insights")
        self.models = {}
        self.insights_cache = {}
        
        # Initialize components
        self.scaler = StandardScaler()
        self.label_encoders = {}
    
    def generate_comprehensive_insights(self, data: List[Dict], 
                                      form_schema: Dict = None,
                                      user_plan: str = "starter",
                                      current_usage: int = 0) -> Dict:
        """
        Generate comprehensive insights from ODK data with subscription awareness.
        
        Args:
            data: List of data records.
            form_schema: Form schema for context.
            user_plan: User's subscription plan.
            current_usage: Current monthly usage count.
            
        Returns:
            Dictionary with comprehensive insights.
        """
        if not self.config["enabled"]:
            return {"status": "disabled", "message": "Data insights are disabled"}
        
        # Check subscription limits
        if not check_subscription_limit("data_insights", user_plan, 
                                      "max_insights_per_month", current_usage):
            return {
                "status": "limit_exceeded",
                "message": f"Monthly insights limit exceeded for {user_plan} plan"
            }
        
        if not data:
            return {"status": "error", "message": "No data provided"}
        
        try:
            # Convert to DataFrame for analysis
            df = pd.DataFrame(data)
            
            # Generate different types of insights
            insights = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "data_summary": self._generate_data_summary(df),
                "statistical_insights": self._generate_statistical_insights(df),
                "correlation_insights": self._generate_correlation_insights(df),
                "trend_insights": self._generate_trend_insights(df),
                "pattern_insights": self._generate_pattern_insights(df),
                "predictive_insights": self._generate_predictive_insights(df),
                "recommendations": self._generate_recommendations(df, form_schema),
                "visualizations": self._suggest_visualizations(df)
            }
            
            # Add auto-insights if enabled
            if self.config.get("auto_insights", True):
                insights["auto_insights"] = self._generate_auto_insights(df)
            
            # Log event
            log_ai_event("comprehensive_insights", {
                "user_plan": user_plan,
                "num_records": len(data),
                "num_insights": sum(len(v) if isinstance(v, list) else 1 
                                  for v in insights.values() if isinstance(v, (list, dict)))
            })
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive insights: {e}")
            return {"status": "error", "message": str(e)}
    
    def generate_real_time_insights(self, new_data: List[Dict], 
                                   historical_data: List[Dict] = None) -> Dict:
        """
        Generate real-time insights as new data arrives.
        
        Args:
            new_data: Newly submitted data.
            historical_data: Historical data for comparison.
            
        Returns:
            Dictionary with real-time insights.
        """
        try:
            insights = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "new_data_summary": self._analyze_new_data(new_data),
                "trends": [],
                "alerts": [],
                "predictions": []
            }
            
            if historical_data:
                # Compare with historical patterns
                insights["comparative_analysis"] = self._compare_with_historical(
                    new_data, historical_data
                )
                
                # Detect emerging trends
                insights["emerging_trends"] = self._detect_emerging_trends(
                    new_data, historical_data
                )
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating real-time insights: {e}")
            return {"status": "error", "message": str(e)}
    
    def _generate_data_summary(self, df: pd.DataFrame) -> Dict:
        """Generate basic data summary statistics."""
        summary = {
            "total_records": len(df),
            "total_fields": len(df.columns),
            "numeric_fields": len(df.select_dtypes(include=[np.number]).columns),
            "categorical_fields": len(df.select_dtypes(include=['object']).columns),
            "missing_data": {},
            "data_types": {}
        }
        
        # Missing data analysis
        for col in df.columns:
            missing_count = df[col].isnull().sum()
            if missing_count > 0:
                summary["missing_data"][col] = {
                    "count": int(missing_count),
                    "percentage": float(missing_count / len(df) * 100)
                }
        
        # Data types
        for col in df.columns:
            summary["data_types"][col] = str(df[col].dtype)
        
        return summary
    
    def _generate_statistical_insights(self, df: pd.DataFrame) -> List[Dict]:
        """Generate statistical insights from the data."""
        insights = []
        
        # Analyze numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].notna().sum() < 2:
                continue
            
            col_data = df[col].dropna()
            
            # Basic statistics
            stats_dict = {
                "field": col,
                "type": "statistical_summary",
                "statistics": {
                    "mean": float(col_data.mean()),
                    "median": float(col_data.median()),
                    "std": float(col_data.std()),
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "q25": float(col_data.quantile(0.25)),
                    "q75": float(col_data.quantile(0.75))
                }
            }
            
            # Distribution analysis
            if len(col_data) > 10:
                # Test for normality
                _, p_value = stats.normaltest(col_data)
                stats_dict["distribution"] = {
                    "is_normal": p_value > 0.05,
                    "p_value": float(p_value),
                    "skewness": float(stats.skew(col_data)),
                    "kurtosis": float(stats.kurtosis(col_data))
                }
            
            insights.append(stats_dict)
        
        # Analyze categorical columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if df[col].notna().sum() < 2:
                continue
            
            col_data = df[col].dropna()
            value_counts = col_data.value_counts()
            
            insights.append({
                "field": col,
                "type": "categorical_summary",
                "statistics": {
                    "unique_values": int(col_data.nunique()),
                    "most_common": str(value_counts.index[0]),
                    "most_common_count": int(value_counts.iloc[0]),
                    "least_common": str(value_counts.index[-1]),
                    "least_common_count": int(value_counts.iloc[-1]),
                    "distribution": value_counts.head(10).to_dict()
                }
            })
        
        return insights
    
    def _generate_correlation_insights(self, df: pd.DataFrame) -> List[Dict]:
        """Generate correlation insights between variables."""
        insights = []
        
        # Get numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return insights
        
        # Calculate correlation matrix
        corr_matrix = df[numeric_cols].corr()
        
        # Find strong correlations
        for i, col1 in enumerate(numeric_cols):
            for j, col2 in enumerate(numeric_cols):
                if i >= j:  # Avoid duplicates and self-correlation
                    continue
                
                correlation = corr_matrix.loc[col1, col2]
                
                if abs(correlation) >= self.config["min_correlation"]:
                    # Calculate p-value
                    _, p_value = stats.pearsonr(df[col1].dropna(), df[col2].dropna())
                    
                    insights.append({
                        "type": "correlation",
                        "field1": col1,
                        "field2": col2,
                        "correlation": float(correlation),
                        "strength": self._get_correlation_strength(correlation),
                        "direction": "positive" if correlation > 0 else "negative",
                        "p_value": float(p_value),
                        "significant": p_value < 0.05,
                        "interpretation": self._interpret_correlation(col1, col2, correlation)
                    })
        
        return insights
    
    def _generate_trend_insights(self, df: pd.DataFrame) -> List[Dict]:
        """Generate trend insights from time-series data."""
        insights = []
        
        # Look for timestamp columns
        timestamp_cols = []
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['time', 'date', 'created', 'submitted']):
                try:
                    pd.to_datetime(df[col])
                    timestamp_cols.append(col)
                except:
                    continue
        
        if not timestamp_cols:
            return insights
        
        # Analyze trends for each timestamp column
        for time_col in timestamp_cols:
            try:
                df_time = df.copy()
                df_time[time_col] = pd.to_datetime(df_time[time_col])
                df_time = df_time.sort_values(time_col)
                
                # Analyze numeric trends over time
                numeric_cols = df_time.select_dtypes(include=[np.number]).columns
                for num_col in numeric_cols:
                    if df_time[num_col].notna().sum() < 5:
                        continue
                    
                    # Calculate trend
                    x = np.arange(len(df_time))
                    y = df_time[num_col].fillna(method='ffill').fillna(method='bfill')
                    
                    if len(y) > 1:
                        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                        
                        insights.append({
                            "type": "trend",
                            "time_field": time_col,
                            "value_field": num_col,
                            "trend_direction": "increasing" if slope > 0 else "decreasing",
                            "slope": float(slope),
                            "r_squared": float(r_value ** 2),
                            "p_value": float(p_value),
                            "significant": p_value < 0.05,
                            "interpretation": self._interpret_trend(num_col, slope, r_value ** 2)
                        })
                
                # Analyze submission patterns over time
                daily_counts = df_time.groupby(df_time[time_col].dt.date).size()
                if len(daily_counts) > 1:
                    insights.append({
                        "type": "submission_pattern",
                        "time_field": time_col,
                        "daily_average": float(daily_counts.mean()),
                        "daily_std": float(daily_counts.std()),
                        "peak_day": str(daily_counts.idxmax()),
                        "peak_count": int(daily_counts.max()),
                        "low_day": str(daily_counts.idxmin()),
                        "low_count": int(daily_counts.min())
                    })
                
            except Exception as e:
                self.logger.error(f"Error analyzing trends for {time_col}: {e}")
                continue
        
        return insights
    
    def _generate_pattern_insights(self, df: pd.DataFrame) -> List[Dict]:
        """Generate pattern insights using clustering and other techniques."""
        insights = []
        
        # Prepare data for clustering
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return insights
        
        # Get clean numeric data
        numeric_data = df[numeric_cols].dropna()
        if len(numeric_data) < 10:
            return insights
        
        try:
            # Standardize the data
            scaled_data = self.scaler.fit_transform(numeric_data)
            
            # Perform clustering
            n_clusters = min(5, len(numeric_data) // 10)  # Reasonable number of clusters
            if n_clusters >= 2:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                clusters = kmeans.fit_predict(scaled_data)
                
                # Analyze clusters
                cluster_analysis = []
                for i in range(n_clusters):
                    cluster_data = numeric_data[clusters == i]
                    cluster_analysis.append({
                        "cluster_id": i,
                        "size": len(cluster_data),
                        "percentage": len(cluster_data) / len(numeric_data) * 100,
                        "characteristics": {
                            col: {
                                "mean": float(cluster_data[col].mean()),
                                "std": float(cluster_data[col].std())
                            }
                            for col in numeric_cols
                        }
                    })
                
                insights.append({
                    "type": "clustering",
                    "method": "k_means",
                    "n_clusters": n_clusters,
                    "clusters": cluster_analysis,
                    "interpretation": self._interpret_clusters(cluster_analysis, numeric_cols)
                })
        
        except Exception as e:
            self.logger.error(f"Error in pattern analysis: {e}")
        
        return insights
    
    def _generate_predictive_insights(self, df: pd.DataFrame) -> List[Dict]:
        """Generate predictive insights using machine learning."""
        insights = []
        
        if not self.config.get("predictive_analytics", True):
            return insights
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return insights
        
        # Try to build predictive models for each numeric target
        for target_col in numeric_cols:
            try:
                # Prepare features and target
                feature_cols = [col for col in numeric_cols if col != target_col]
                if not feature_cols:
                    continue
                
                # Get clean data
                clean_data = df[feature_cols + [target_col]].dropna()
                if len(clean_data) < 20:  # Need sufficient data
                    continue
                
                X = clean_data[feature_cols]
                y = clean_data[target_col]
                
                # Split data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.3, random_state=42
                )
                
                # Train model
                model = RandomForestRegressor(n_estimators=50, random_state=42)
                model.fit(X_train, y_train)
                
                # Evaluate model
                y_pred = model.predict(X_test)
                mse = mean_squared_error(y_test, y_pred)
                r2_score = model.score(X_test, y_test)
                
                # Feature importance
                feature_importance = dict(zip(feature_cols, model.feature_importances_))
                
                insights.append({
                    "type": "predictive_model",
                    "target_field": target_col,
                    "model_type": "random_forest_regressor",
                    "performance": {
                        "r2_score": float(r2_score),
                        "mse": float(mse),
                        "rmse": float(np.sqrt(mse))
                    },
                    "feature_importance": {k: float(v) for k, v in feature_importance.items()},
                    "most_important_feature": max(feature_importance, key=feature_importance.get),
                    "interpretation": self._interpret_prediction_model(target_col, feature_importance, r2_score)
                })
                
                # Store model for future predictions
                self.models[f"predict_{target_col}"] = model
                
            except Exception as e:
                self.logger.error(f"Error building predictive model for {target_col}: {e}")
                continue
        
        return insights
    
    def _generate_recommendations(self, df: pd.DataFrame, form_schema: Dict = None) -> List[Dict]:
        """Generate actionable recommendations based on insights."""
        recommendations = []
        
        # Data quality recommendations
        missing_data_threshold = 0.1  # 10%
        for col in df.columns:
            missing_pct = df[col].isnull().sum() / len(df)
            if missing_pct > missing_data_threshold:
                recommendations.append({
                    "type": "data_quality",
                    "priority": "high" if missing_pct > 0.3 else "medium",
                    "field": col,
                    "issue": "high_missing_data",
                    "description": f"Field '{col}' has {missing_pct:.1%} missing data",
                    "recommendation": f"Consider making '{col}' required or provide default values",
                    "impact": "Data completeness and analysis accuracy"
                })
        
        # Form design recommendations
        if form_schema:
            recommendations.extend(self._generate_form_recommendations(df, form_schema))
        
        # Analysis recommendations
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 1:
            recommendations.append({
                "type": "analysis",
                "priority": "medium",
                "description": "Multiple numeric fields detected",
                "recommendation": "Consider correlation analysis and predictive modeling",
                "impact": "Better understanding of relationships between variables"
            })
        
        # Visualization recommendations
        recommendations.extend(self._generate_visualization_recommendations(df))
        
        return recommendations
    
    def _suggest_visualizations(self, df: pd.DataFrame) -> List[Dict]:
        """Suggest appropriate visualizations for the data."""
        suggestions = []
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        # Single variable visualizations
        for col in numeric_cols:
            suggestions.append({
                "type": "histogram",
                "field": col,
                "purpose": "Show distribution of values",
                "priority": "medium"
            })
            
            suggestions.append({
                "type": "box_plot",
                "field": col,
                "purpose": "Identify outliers and quartiles",
                "priority": "medium"
            })
        
        for col in categorical_cols:
            if df[col].nunique() <= 20:  # Reasonable number of categories
                suggestions.append({
                    "type": "bar_chart",
                    "field": col,
                    "purpose": "Show frequency of categories",
                    "priority": "high"
                })
        
        # Two variable visualizations
        if len(numeric_cols) >= 2:
            for i, col1 in enumerate(numeric_cols):
                for col2 in numeric_cols[i+1:]:
                    suggestions.append({
                        "type": "scatter_plot",
                        "fields": [col1, col2],
                        "purpose": "Show relationship between variables",
                        "priority": "high"
                    })
        
        # Time series visualizations
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['time', 'date', 'created', 'submitted']):
                suggestions.append({
                    "type": "time_series",
                    "field": col,
                    "purpose": "Show trends over time",
                    "priority": "high"
                })
        
        # Geographic visualizations
        if any(keyword in str(df.columns).lower() for keyword in ['lat', 'lon', 'gps', 'location']):
            suggestions.append({
                "type": "map",
                "purpose": "Show geographic distribution",
                "priority": "high"
            })
        
        return suggestions
    
    def _generate_auto_insights(self, df: pd.DataFrame) -> List[str]:
        """Generate automatic insights in natural language."""
        insights = []
        
        # Data overview
        insights.append(f"Dataset contains {len(df)} records with {len(df.columns)} fields")
        
        # Missing data insights
        missing_cols = [col for col in df.columns if df[col].isnull().sum() > 0]
        if missing_cols:
            insights.append(f"{len(missing_cols)} fields have missing data")
        
        # Numeric insights
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            insights.append(f"Found {len(numeric_cols)} numeric fields for quantitative analysis")
            
            # Find most variable field
            if len(numeric_cols) > 1:
                cv_values = {}
                for col in numeric_cols:
                    if df[col].std() > 0:
                        cv_values[col] = df[col].std() / df[col].mean()
                
                if cv_values:
                    most_variable = max(cv_values, key=cv_values.get)
                    insights.append(f"'{most_variable}' shows the highest variability")
        
        # Categorical insights
        categorical_cols = df.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 0:
            insights.append(f"Found {len(categorical_cols)} categorical fields")
            
            # Find most diverse field
            diversity_scores = {}
            for col in categorical_cols:
                unique_ratio = df[col].nunique() / len(df)
                diversity_scores[col] = unique_ratio
            
            if diversity_scores:
                most_diverse = max(diversity_scores, key=diversity_scores.get)
                insights.append(f"'{most_diverse}' has the most diverse responses")
        
        return insights
    
    def _analyze_new_data(self, new_data: List[Dict]) -> Dict:
        """Analyze newly submitted data."""
        df = pd.DataFrame(new_data)
        
        return {
            "record_count": len(df),
            "submission_rate": "real_time",
            "data_quality": {
                "completeness": (1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100,
                "fields_with_data": len([col for col in df.columns if df[col].notna().any()])
            }
        }
    
    def _compare_with_historical(self, new_data: List[Dict], 
                                historical_data: List[Dict]) -> Dict:
        """Compare new data with historical patterns."""
        new_df = pd.DataFrame(new_data)
        hist_df = pd.DataFrame(historical_data)
        
        comparison = {
            "volume_change": len(new_data) / len(historical_data) * 100 - 100,
            "field_changes": [],
            "pattern_changes": []
        }
        
        # Compare field distributions
        common_fields = set(new_df.columns) & set(hist_df.columns)
        for field in common_fields:
            if pd.api.types.is_numeric_dtype(new_df[field]):
                new_mean = new_df[field].mean()
                hist_mean = hist_df[field].mean()
                change_pct = (new_mean - hist_mean) / hist_mean * 100 if hist_mean != 0 else 0
                
                if abs(change_pct) > 10:  # Significant change
                    comparison["field_changes"].append({
                        "field": field,
                        "change_percentage": change_pct,
                        "direction": "increase" if change_pct > 0 else "decrease"
                    })
        
        return comparison
    
    def _detect_emerging_trends(self, new_data: List[Dict], 
                               historical_data: List[Dict]) -> List[Dict]:
        """Detect emerging trends in the data."""
        trends = []
        
        # This would involve more sophisticated trend detection algorithms
        # For now, implementing basic trend detection
        
        return trends
    
    def _get_correlation_strength(self, correlation: float) -> str:
        """Get correlation strength description."""
        abs_corr = abs(correlation)
        if abs_corr >= 0.8:
            return "very_strong"
        elif abs_corr >= 0.6:
            return "strong"
        elif abs_corr >= 0.4:
            return "moderate"
        elif abs_corr >= 0.2:
            return "weak"
        else:
            return "very_weak"
    
    def _interpret_correlation(self, field1: str, field2: str, correlation: float) -> str:
        """Interpret correlation between two fields."""
        direction = "positively" if correlation > 0 else "negatively"
        strength = self._get_correlation_strength(correlation)
        
        return f"'{field1}' and '{field2}' are {strength} {direction} correlated"
    
    def _interpret_trend(self, field: str, slope: float, r_squared: float) -> str:
        """Interpret trend analysis results."""
        direction = "increasing" if slope > 0 else "decreasing"
        strength = "strong" if r_squared > 0.7 else "moderate" if r_squared > 0.3 else "weak"
        
        return f"'{field}' shows a {strength} {direction} trend over time"
    
    def _interpret_clusters(self, cluster_analysis: List[Dict], fields: List[str]) -> str:
        """Interpret clustering results."""
        n_clusters = len(cluster_analysis)
        largest_cluster = max(cluster_analysis, key=lambda x: x["size"])
        
        return f"Data naturally groups into {n_clusters} distinct patterns, with the largest group representing {largest_cluster['percentage']:.1f}% of records"
    
    def _interpret_prediction_model(self, target: str, feature_importance: Dict, r2_score: float) -> str:
        """Interpret predictive model results."""
        most_important = max(feature_importance, key=feature_importance.get)
        accuracy = "high" if r2_score > 0.7 else "moderate" if r2_score > 0.3 else "low"
        
        return f"'{target}' can be predicted with {accuracy} accuracy, with '{most_important}' being the most influential factor"
    
    def _generate_form_recommendations(self, df: pd.DataFrame, form_schema: Dict) -> List[Dict]:
        """Generate form design recommendations."""
        recommendations = []
        
        # This would analyze the form schema and data to suggest improvements
        # For now, implementing basic recommendations
        
        return recommendations
    
    def _generate_visualization_recommendations(self, df: pd.DataFrame) -> List[Dict]:
        """Generate visualization recommendations."""
        recommendations = []
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        if len(numeric_cols) >= 2:
            recommendations.append({
                "type": "visualization",
                "priority": "high",
                "description": "Multiple numeric fields available",
                "recommendation": "Create correlation heatmap and scatter plots",
                "impact": "Better understanding of variable relationships"
            })
        
        if len(categorical_cols) > 0:
            recommendations.append({
                "type": "visualization",
                "priority": "medium",
                "description": "Categorical data available",
                "recommendation": "Create bar charts and pie charts for category distributions",
                "impact": "Clear visualization of categorical patterns"
            })
        
        return recommendations

