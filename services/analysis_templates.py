"""
Analysis Templates and Report Generation System
Comprehensive templates for NGOs, Think Tanks, and CSR Organizations
"""

import os
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import logging
from dataclasses import dataclass
from enum import Enum
import uuid
from jinja2 import Template
import pdfkit
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import io
import base64
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalysisType(Enum):
    """Types of analysis templates"""
    IMPACT_ASSESSMENT = "impact_assessment"
    DEMOGRAPHIC_ANALYSIS = "demographic_analysis"
    GEOGRAPHIC_DISTRIBUTION = "geographic_distribution"
    TEMPORAL_TRENDS = "temporal_trends"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    STATISTICAL_SUMMARY = "statistical_summary"
    CORRELATION_ANALYSIS = "correlation_analysis"
    REGRESSION_ANALYSIS = "regression_analysis"
    SURVEY_ANALYSIS = "survey_analysis"
    PROGRAM_EVALUATION = "program_evaluation"
    BENEFICIARY_TRACKING = "beneficiary_tracking"
    RESOURCE_ALLOCATION = "resource_allocation"
    OUTCOME_MEASUREMENT = "outcome_measurement"
    STAKEHOLDER_FEEDBACK = "stakeholder_feedback"
    COMPLIANCE_REPORTING = "compliance_reporting"

class OrganizationType(Enum):
    """Target organization types"""
    NGO = "ngo"
    THINK_TANK = "think_tank"
    CSR_FIRM = "csr_firm"
    RESEARCH_INSTITUTE = "research_institute"
    GOVERNMENT = "government"
    INTERNATIONAL_ORG = "international_org"

@dataclass
class AnalysisTemplate:
    """Analysis template configuration"""
    id: str
    name: str
    description: str
    analysis_type: AnalysisType
    target_organizations: List[OrganizationType]
    required_fields: List[str]
    optional_fields: List[str]
    visualizations: List[str]
    statistical_methods: List[str]
    output_formats: List[str]
    template_config: Dict[str, Any]

class AnalysisTemplateManager:
    """
    Comprehensive analysis template manager for social sector organizations
    """
    
    def __init__(self):
        self.templates = {}
        self.initialize_templates()
    
    def initialize_templates(self):
        """Initialize all analysis templates"""
        
        # Impact Assessment Template for NGOs
        self.templates['impact_assessment_ngo'] = AnalysisTemplate(
            id='impact_assessment_ngo',
            name='NGO Impact Assessment',
            description='Comprehensive impact measurement for NGO programs and interventions',
            analysis_type=AnalysisType.IMPACT_ASSESSMENT,
            target_organizations=[OrganizationType.NGO, OrganizationType.INTERNATIONAL_ORG],
            required_fields=['beneficiary_id', 'program_id', 'baseline_metrics', 'outcome_metrics', 'date'],
            optional_fields=['demographics', 'location', 'intervention_type', 'cost_data'],
            visualizations=['before_after_comparison', 'impact_distribution', 'geographic_heatmap', 'trend_analysis'],
            statistical_methods=['paired_t_test', 'effect_size', 'confidence_intervals', 'regression_analysis'],
            output_formats=['pdf_report', 'dashboard', 'excel_export', 'presentation'],
            template_config={
                'significance_level': 0.05,
                'confidence_level': 0.95,
                'minimum_sample_size': 30,
                'impact_metrics': ['health_outcomes', 'education_scores', 'income_levels', 'quality_of_life']
            }
        )
        
        # Demographic Analysis Template
        self.templates['demographic_analysis'] = AnalysisTemplate(
            id='demographic_analysis',
            name='Demographic Distribution Analysis',
            description='Comprehensive demographic analysis for program targeting and evaluation',
            analysis_type=AnalysisType.DEMOGRAPHIC_ANALYSIS,
            target_organizations=[OrganizationType.NGO, OrganizationType.CSR_FIRM, OrganizationType.GOVERNMENT],
            required_fields=['age', 'gender', 'location'],
            optional_fields=['education', 'income', 'occupation', 'household_size', 'ethnicity'],
            visualizations=['age_pyramid', 'gender_distribution', 'education_levels', 'income_brackets', 'geographic_distribution'],
            statistical_methods=['descriptive_statistics', 'chi_square_test', 'anova', 'correlation_analysis'],
            output_formats=['pdf_report', 'interactive_dashboard', 'csv_export'],
            template_config={
                'age_groups': ['0-17', '18-35', '36-55', '56-65', '65+'],
                'income_brackets': ['<$10k', '$10k-$25k', '$25k-$50k', '$50k-$100k', '>$100k'],
                'education_levels': ['No formal education', 'Primary', 'Secondary', 'Higher education']
            }
        )
        
        # Think Tank Research Analysis Template
        self.templates['research_analysis_think_tank'] = AnalysisTemplate(
            id='research_analysis_think_tank',
            name='Think Tank Research Analysis',
            description='Advanced statistical analysis for policy research and evidence-based recommendations',
            analysis_type=AnalysisType.STATISTICAL_SUMMARY,
            target_organizations=[OrganizationType.THINK_TANK, OrganizationType.RESEARCH_INSTITUTE],
            required_fields=['research_question', 'data_source', 'methodology', 'variables'],
            optional_fields=['control_variables', 'sample_weights', 'geographic_scope', 'time_period'],
            visualizations=['regression_plots', 'correlation_matrix', 'distribution_plots', 'confidence_intervals'],
            statistical_methods=['multiple_regression', 'logistic_regression', 'time_series_analysis', 'causal_inference'],
            output_formats=['academic_paper', 'policy_brief', 'technical_report', 'presentation'],
            template_config={
                'statistical_software': 'python',
                'significance_levels': [0.01, 0.05, 0.10],
                'robustness_checks': True,
                'publication_ready': True
            }
        )
        
        # CSR Impact Measurement Template
        self.templates['csr_impact_measurement'] = AnalysisTemplate(
            id='csr_impact_measurement',
            name='CSR Impact Measurement',
            description='Corporate Social Responsibility impact assessment and ROI analysis',
            analysis_type=AnalysisType.PROGRAM_EVALUATION,
            target_organizations=[OrganizationType.CSR_FIRM],
            required_fields=['program_name', 'investment_amount', 'beneficiaries', 'outcomes', 'timeline'],
            optional_fields=['stakeholder_feedback', 'media_coverage', 'employee_engagement', 'brand_impact'],
            visualizations=['roi_analysis', 'stakeholder_impact', 'timeline_progress', 'cost_effectiveness'],
            statistical_methods=['cost_benefit_analysis', 'social_return_on_investment', 'impact_attribution'],
            output_formats=['executive_summary', 'board_presentation', 'sustainability_report', 'stakeholder_report'],
            template_config={
                'roi_calculation_method': 'social_roi',
                'stakeholder_categories': ['employees', 'customers', 'community', 'environment'],
                'impact_valuation': True,
                'materiality_assessment': True
            }
        )
        
        # Geographic Distribution Analysis Template
        self.templates['geographic_analysis'] = AnalysisTemplate(
            id='geographic_analysis',
            name='Geographic Distribution Analysis',
            description='Spatial analysis of program reach and impact across different regions',
            analysis_type=AnalysisType.GEOGRAPHIC_DISTRIBUTION,
            target_organizations=[OrganizationType.NGO, OrganizationType.GOVERNMENT, OrganizationType.INTERNATIONAL_ORG],
            required_fields=['latitude', 'longitude', 'region', 'program_data'],
            optional_fields=['population_density', 'socioeconomic_indicators', 'infrastructure_data'],
            visualizations=['choropleth_maps', 'heat_maps', 'cluster_analysis', 'accessibility_maps'],
            statistical_methods=['spatial_autocorrelation', 'hotspot_analysis', 'geographic_clustering'],
            output_formats=['interactive_map', 'pdf_report', 'gis_export'],
            template_config={
                'map_projection': 'mercator',
                'clustering_algorithm': 'kmeans',
                'spatial_resolution': 'admin_level_2',
                'basemap_style': 'openstreetmap'
            }
        )
        
        # Temporal Trends Analysis Template
        self.templates['temporal_trends'] = AnalysisTemplate(
            id='temporal_trends',
            name='Temporal Trends Analysis',
            description='Time series analysis of program performance and outcome trends',
            analysis_type=AnalysisType.TEMPORAL_TRENDS,
            target_organizations=[OrganizationType.NGO, OrganizationType.CSR_FIRM, OrganizationType.THINK_TANK],
            required_fields=['date', 'metric_value', 'metric_type'],
            optional_fields=['seasonal_factors', 'external_events', 'intervention_dates'],
            visualizations=['time_series_plots', 'seasonal_decomposition', 'trend_forecasting', 'change_point_detection'],
            statistical_methods=['time_series_analysis', 'seasonal_adjustment', 'forecasting', 'trend_testing'],
            output_formats=['trend_report', 'forecast_dashboard', 'statistical_summary'],
            template_config={
                'forecasting_horizon': 12,  # months
                'seasonality_detection': True,
                'trend_significance_test': True,
                'anomaly_detection': True
            }
        )
        
        # Survey Analysis Template
        self.templates['survey_analysis'] = AnalysisTemplate(
            id='survey_analysis',
            name='Survey Data Analysis',
            description='Comprehensive analysis of survey responses and feedback data',
            analysis_type=AnalysisType.SURVEY_ANALYSIS,
            target_organizations=[OrganizationType.NGO, OrganizationType.CSR_FIRM, OrganizationType.RESEARCH_INSTITUTE],
            required_fields=['respondent_id', 'survey_responses', 'response_date'],
            optional_fields=['demographics', 'response_time', 'survey_method', 'completion_rate'],
            visualizations=['response_distribution', 'likert_scale_analysis', 'cross_tabulation', 'sentiment_analysis'],
            statistical_methods=['descriptive_statistics', 'factor_analysis', 'reliability_analysis', 'sentiment_scoring'],
            output_formats=['survey_report', 'infographic', 'dashboard', 'raw_data_export'],
            template_config={
                'likert_scale_range': [1, 5],
                'response_rate_threshold': 0.3,
                'statistical_significance': 0.05,
                'text_analysis_enabled': True
            }
        )
        
        # Comparative Analysis Template
        self.templates['comparative_analysis'] = AnalysisTemplate(
            id='comparative_analysis',
            name='Comparative Program Analysis',
            description='Cross-project and cross-organization comparative analysis',
            analysis_type=AnalysisType.COMPARATIVE_ANALYSIS,
            target_organizations=[OrganizationType.NGO, OrganizationType.THINK_TANK, OrganizationType.INTERNATIONAL_ORG],
            required_fields=['project_id', 'organization_id', 'outcome_metrics', 'context_variables'],
            optional_fields=['cost_data', 'implementation_approach', 'target_population', 'duration'],
            visualizations=['comparative_charts', 'benchmarking_analysis', 'performance_matrix', 'best_practices_identification'],
            statistical_methods=['anova', 'post_hoc_tests', 'effect_size_comparison', 'meta_analysis'],
            output_formats=['comparative_report', 'benchmarking_dashboard', 'best_practices_guide'],
            template_config={
                'comparison_dimensions': ['effectiveness', 'efficiency', 'sustainability', 'scalability'],
                'normalization_method': 'z_score',
                'outlier_detection': True,
                'confidence_intervals': True
            }
        )

class ReportGenerator:
    """
    Advanced report generation system for analysis templates
    """
    
    def __init__(self, template_manager: AnalysisTemplateManager):
        self.template_manager = template_manager
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom report styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2E86AB'),
            alignment=1  # Center alignment
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#A23B72')
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            leading=14
        ))
    
    def generate_impact_assessment_report(self, data: pd.DataFrame, 
                                        template_id: str = 'impact_assessment_ngo') -> Dict[str, Any]:
        """Generate comprehensive impact assessment report"""
        
        template = self.template_manager.templates[template_id]
        results = {}
        
        # Data validation
        missing_fields = [field for field in template.required_fields if field not in data.columns]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        # Statistical Analysis
        results['statistical_analysis'] = self._perform_impact_analysis(data, template)
        
        # Visualizations
        results['visualizations'] = self._create_impact_visualizations(data, template)
        
        # Summary Statistics
        results['summary_statistics'] = self._calculate_summary_statistics(data, template)
        
        # Recommendations
        results['recommendations'] = self._generate_recommendations(results, template)
        
        # Generate PDF Report
        results['pdf_report'] = self._create_pdf_report(results, template)
        
        return results
    
    def _perform_impact_analysis(self, data: pd.DataFrame, template: AnalysisTemplate) -> Dict[str, Any]:
        """Perform statistical impact analysis"""
        
        analysis_results = {}
        
        # Before-After Analysis (if baseline and outcome metrics available)
        if 'baseline_metrics' in data.columns and 'outcome_metrics' in data.columns:
            baseline = pd.to_numeric(data['baseline_metrics'], errors='coerce').dropna()
            outcome = pd.to_numeric(data['outcome_metrics'], errors='coerce').dropna()
            
            # Paired t-test
            if len(baseline) == len(outcome) and len(baseline) >= template.template_config['minimum_sample_size']:
                t_stat, p_value = stats.ttest_rel(outcome, baseline)
                effect_size = (outcome.mean() - baseline.mean()) / baseline.std()
                
                analysis_results['paired_t_test'] = {
                    'statistic': t_stat,
                    'p_value': p_value,
                    'effect_size': effect_size,
                    'significant': p_value < template.template_config['significance_level'],
                    'baseline_mean': baseline.mean(),
                    'outcome_mean': outcome.mean(),
                    'improvement': ((outcome.mean() - baseline.mean()) / baseline.mean()) * 100
                }
                
                # Confidence interval for the difference
                diff = outcome - baseline
                ci_lower, ci_upper = stats.t.interval(
                    template.template_config['confidence_level'],
                    len(diff) - 1,
                    loc=diff.mean(),
                    scale=stats.sem(diff)
                )
                
                analysis_results['confidence_interval'] = {
                    'lower': ci_lower,
                    'upper': ci_upper,
                    'confidence_level': template.template_config['confidence_level']
                }
        
        # Demographic Impact Analysis
        if 'demographics' in data.columns:
            demographic_analysis = {}
            demographics = data['demographics'].value_counts()
            
            for demo_group in demographics.index:
                group_data = data[data['demographics'] == demo_group]
                if 'outcome_metrics' in group_data.columns:
                    group_outcomes = pd.to_numeric(group_data['outcome_metrics'], errors='coerce').dropna()
                    demographic_analysis[demo_group] = {
                        'count': len(group_data),
                        'mean_outcome': group_outcomes.mean(),
                        'std_outcome': group_outcomes.std(),
                        'median_outcome': group_outcomes.median()
                    }
            
            analysis_results['demographic_analysis'] = demographic_analysis
        
        # Geographic Impact Analysis
        if 'location' in data.columns:
            location_analysis = {}
            locations = data['location'].value_counts()
            
            for location in locations.index:
                location_data = data[data['location'] == location]
                if 'outcome_metrics' in location_data.columns:
                    location_outcomes = pd.to_numeric(location_data['outcome_metrics'], errors='coerce').dropna()
                    location_analysis[location] = {
                        'count': len(location_data),
                        'mean_outcome': location_outcomes.mean(),
                        'std_outcome': location_outcomes.std()
                    }
            
            analysis_results['geographic_analysis'] = location_analysis
        
        return analysis_results
    
    def _create_impact_visualizations(self, data: pd.DataFrame, template: AnalysisTemplate) -> Dict[str, str]:
        """Create impact assessment visualizations"""
        
        visualizations = {}
        
        # Before-After Comparison
        if 'baseline_metrics' in data.columns and 'outcome_metrics' in data.columns:
            baseline = pd.to_numeric(data['baseline_metrics'], errors='coerce').dropna()
            outcome = pd.to_numeric(data['outcome_metrics'], errors='coerce').dropna()
            
            fig = go.Figure()
            
            fig.add_trace(go.Box(
                y=baseline,
                name='Baseline',
                boxpoints='all',
                jitter=0.3,
                pointpos=-1.8,
                marker_color='lightblue'
            ))
            
            fig.add_trace(go.Box(
                y=outcome,
                name='Outcome',
                boxpoints='all',
                jitter=0.3,
                pointpos=-1.8,
                marker_color='lightgreen'
            ))
            
            fig.update_layout(
                title='Before-After Impact Comparison',
                yaxis_title='Metric Value',
                showlegend=True,
                template='plotly_white'
            )
            
            visualizations['before_after_comparison'] = fig.to_html(include_plotlyjs='cdn')
        
        # Impact Distribution
        if 'outcome_metrics' in data.columns:
            outcomes = pd.to_numeric(data['outcome_metrics'], errors='coerce').dropna()
            
            fig = px.histogram(
                x=outcomes,
                nbins=20,
                title='Distribution of Outcome Metrics',
                labels={'x': 'Outcome Value', 'y': 'Frequency'},
                template='plotly_white'
            )
            
            fig.add_vline(
                x=outcomes.mean(),
                line_dash="dash",
                line_color="red",
                annotation_text=f"Mean: {outcomes.mean():.2f}"
            )
            
            visualizations['impact_distribution'] = fig.to_html(include_plotlyjs='cdn')
        
        # Geographic Heatmap
        if all(col in data.columns for col in ['location', 'outcome_metrics']):
            location_summary = data.groupby('location')['outcome_metrics'].agg(['mean', 'count']).reset_index()
            location_summary['outcome_metrics_mean'] = pd.to_numeric(location_summary['mean'], errors='coerce')
            
            fig = px.bar(
                location_summary,
                x='location',
                y='outcome_metrics_mean',
                title='Average Outcomes by Location',
                labels={'outcome_metrics_mean': 'Average Outcome', 'location': 'Location'},
                template='plotly_white'
            )
            
            visualizations['geographic_heatmap'] = fig.to_html(include_plotlyjs='cdn')
        
        # Trend Analysis (if date column available)
        if 'date' in data.columns and 'outcome_metrics' in data.columns:
            data['date'] = pd.to_datetime(data['date'], errors='coerce')
            trend_data = data.dropna(subset=['date', 'outcome_metrics'])
            trend_data = trend_data.groupby(trend_data['date'].dt.to_period('M'))['outcome_metrics'].mean().reset_index()
            trend_data['date'] = trend_data['date'].dt.to_timestamp()
            
            fig = px.line(
                trend_data,
                x='date',
                y='outcome_metrics',
                title='Outcome Trends Over Time',
                labels={'outcome_metrics': 'Average Outcome', 'date': 'Date'},
                template='plotly_white'
            )
            
            visualizations['trend_analysis'] = fig.to_html(include_plotlyjs='cdn')
        
        return visualizations
    
    def _calculate_summary_statistics(self, data: pd.DataFrame, template: AnalysisTemplate) -> Dict[str, Any]:
        """Calculate comprehensive summary statistics"""
        
        summary = {}
        
        # Basic statistics
        summary['total_records'] = len(data)
        summary['analysis_date'] = datetime.now().isoformat()
        summary['template_used'] = template.name
        
        # Outcome metrics summary
        if 'outcome_metrics' in data.columns:
            outcomes = pd.to_numeric(data['outcome_metrics'], errors='coerce').dropna()
            summary['outcome_statistics'] = {
                'count': len(outcomes),
                'mean': outcomes.mean(),
                'median': outcomes.median(),
                'std': outcomes.std(),
                'min': outcomes.min(),
                'max': outcomes.max(),
                'q25': outcomes.quantile(0.25),
                'q75': outcomes.quantile(0.75)
            }
        
        # Demographic breakdown
        if 'demographics' in data.columns:
            demo_counts = data['demographics'].value_counts().to_dict()
            summary['demographic_breakdown'] = demo_counts
        
        # Geographic breakdown
        if 'location' in data.columns:
            location_counts = data['location'].value_counts().to_dict()
            summary['geographic_breakdown'] = location_counts
        
        # Program breakdown
        if 'program_id' in data.columns:
            program_counts = data['program_id'].value_counts().to_dict()
            summary['program_breakdown'] = program_counts
        
        return summary
    
    def _generate_recommendations(self, results: Dict[str, Any], template: AnalysisTemplate) -> List[str]:
        """Generate data-driven recommendations"""
        
        recommendations = []
        
        # Statistical significance recommendations
        if 'statistical_analysis' in results and 'paired_t_test' in results['statistical_analysis']:
            t_test = results['statistical_analysis']['paired_t_test']
            
            if t_test['significant']:
                if t_test['improvement'] > 0:
                    recommendations.append(
                        f"The program shows statistically significant positive impact "
                        f"({t_test['improvement']:.1f}% improvement, p={t_test['p_value']:.3f}). "
                        f"Consider scaling this intervention."
                    )
                else:
                    recommendations.append(
                        f"The program shows statistically significant negative impact "
                        f"({t_test['improvement']:.1f}% decline, p={t_test['p_value']:.3f}). "
                        f"Immediate program review and modification recommended."
                    )
            else:
                recommendations.append(
                    f"No statistically significant impact detected (p={t_test['p_value']:.3f}). "
                    f"Consider increasing sample size or modifying intervention approach."
                )
        
        # Effect size recommendations
        if 'statistical_analysis' in results and 'paired_t_test' in results['statistical_analysis']:
            effect_size = results['statistical_analysis']['paired_t_test']['effect_size']
            
            if abs(effect_size) < 0.2:
                recommendations.append("Small effect size detected. Consider program enhancements to increase impact.")
            elif abs(effect_size) < 0.5:
                recommendations.append("Medium effect size achieved. Good program performance with room for improvement.")
            else:
                recommendations.append("Large effect size achieved. Excellent program performance - consider replication.")
        
        # Demographic recommendations
        if 'statistical_analysis' in results and 'demographic_analysis' in results['statistical_analysis']:
            demo_analysis = results['statistical_analysis']['demographic_analysis']
            
            # Find best and worst performing demographic groups
            if demo_analysis:
                group_outcomes = {group: data['mean_outcome'] for group, data in demo_analysis.items() 
                                if 'mean_outcome' in data and not pd.isna(data['mean_outcome'])}
                
                if group_outcomes:
                    best_group = max(group_outcomes, key=group_outcomes.get)
                    worst_group = min(group_outcomes, key=group_outcomes.get)
                    
                    recommendations.append(
                        f"Demographic group '{best_group}' shows highest outcomes "
                        f"({group_outcomes[best_group]:.2f}). Consider studying success factors for replication."
                    )
                    
                    recommendations.append(
                        f"Demographic group '{worst_group}' shows lowest outcomes "
                        f"({group_outcomes[worst_group]:.2f}). Targeted interventions recommended."
                    )
        
        # Sample size recommendations
        if 'summary_statistics' in results:
            total_records = results['summary_statistics']['total_records']
            min_sample = template.template_config.get('minimum_sample_size', 30)
            
            if total_records < min_sample:
                recommendations.append(
                    f"Sample size ({total_records}) is below recommended minimum ({min_sample}). "
                    f"Increase data collection for more reliable results."
                )
            elif total_records < min_sample * 2:
                recommendations.append(
                    f"Sample size ({total_records}) is adequate but could be larger for increased statistical power."
                )
        
        # Data quality recommendations
        if 'outcome_statistics' in results.get('summary_statistics', {}):
            outcome_stats = results['summary_statistics']['outcome_statistics']
            
            if outcome_stats['std'] > outcome_stats['mean']:
                recommendations.append(
                    "High variability in outcomes detected. Consider investigating factors contributing to variation."
                )
        
        return recommendations
    
    def _create_pdf_report(self, results: Dict[str, Any], template: AnalysisTemplate) -> str:
        """Create comprehensive PDF report"""
        
        # Create temporary file for PDF
        pdf_filename = f"/tmp/impact_report_{uuid.uuid4().hex[:8]}.pdf"
        
        doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
        story = []
        
        # Title
        title = Paragraph(f"{template.name} Report", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", self.styles['CustomHeading']))
        
        if 'summary_statistics' in results:
            summary = results['summary_statistics']
            summary_text = f"""
            This report presents the analysis of {summary['total_records']} records using the {template.name} template.
            The analysis was conducted on {summary['analysis_date'][:10]} and includes statistical analysis,
            visualizations, and data-driven recommendations.
            """
            story.append(Paragraph(summary_text, self.styles['CustomBody']))
        
        story.append(Spacer(1, 12))
        
        # Statistical Results
        if 'statistical_analysis' in results:
            story.append(Paragraph("Statistical Analysis Results", self.styles['CustomHeading']))
            
            if 'paired_t_test' in results['statistical_analysis']:
                t_test = results['statistical_analysis']['paired_t_test']
                
                stats_text = f"""
                <b>Impact Analysis:</b><br/>
                • Baseline Mean: {t_test['baseline_mean']:.2f}<br/>
                • Outcome Mean: {t_test['outcome_mean']:.2f}<br/>
                • Improvement: {t_test['improvement']:.1f}%<br/>
                • Statistical Significance: {'Yes' if t_test['significant'] else 'No'} (p={t_test['p_value']:.3f})<br/>
                • Effect Size: {t_test['effect_size']:.3f}
                """
                story.append(Paragraph(stats_text, self.styles['CustomBody']))
            
            story.append(Spacer(1, 12))
        
        # Recommendations
        if 'recommendations' in results:
            story.append(Paragraph("Recommendations", self.styles['CustomHeading']))
            
            for i, recommendation in enumerate(results['recommendations'], 1):
                rec_text = f"{i}. {recommendation}"
                story.append(Paragraph(rec_text, self.styles['CustomBody']))
            
            story.append(Spacer(1, 12))
        
        # Summary Statistics Table
        if 'summary_statistics' in results and 'outcome_statistics' in results['summary_statistics']:
            story.append(Paragraph("Summary Statistics", self.styles['CustomHeading']))
            
            outcome_stats = results['summary_statistics']['outcome_statistics']
            
            stats_data = [
                ['Statistic', 'Value'],
                ['Count', f"{outcome_stats['count']:,}"],
                ['Mean', f"{outcome_stats['mean']:.2f}"],
                ['Median', f"{outcome_stats['median']:.2f}"],
                ['Standard Deviation', f"{outcome_stats['std']:.2f}"],
                ['Minimum', f"{outcome_stats['min']:.2f}"],
                ['Maximum', f"{outcome_stats['max']:.2f}"],
                ['25th Percentile', f"{outcome_stats['q25']:.2f}"],
                ['75th Percentile', f"{outcome_stats['q75']:.2f}"]
            ]
            
            stats_table = Table(stats_data)
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(stats_table)
        
        # Build PDF
        doc.build(story)
        
        return pdf_filename

# Example usage and template testing
if __name__ == '__main__':
    # Initialize template manager
    template_manager = AnalysisTemplateManager()
    report_generator = ReportGenerator(template_manager)
    
    # Generate sample data for testing
    np.random.seed(42)
    n_samples = 200
    
    sample_data = pd.DataFrame({
        'beneficiary_id': [f"BEN_{i:04d}" for i in range(n_samples)],
        'program_id': np.random.choice(['PROG_001', 'PROG_002', 'PROG_003'], n_samples),
        'baseline_metrics': np.random.normal(50, 15, n_samples),
        'outcome_metrics': np.random.normal(65, 18, n_samples),  # Simulated improvement
        'date': pd.date_range('2023-01-01', periods=n_samples, freq='D'),
        'demographics': np.random.choice(['Youth', 'Adult', 'Senior'], n_samples),
        'location': np.random.choice(['Urban', 'Rural', 'Semi-Urban'], n_samples)
    })
    
    # Generate impact assessment report
    try:
        results = report_generator.generate_impact_assessment_report(sample_data)
        
        print("✅ Impact Assessment Report Generated Successfully!")
        print(f"📊 Total Records Analyzed: {results['summary_statistics']['total_records']}")
        print(f"📈 Statistical Significance: {results['statistical_analysis']['paired_t_test']['significant']}")
        print(f"📋 Recommendations Generated: {len(results['recommendations'])}")
        print(f"📄 PDF Report: {results['pdf_report']}")
        
        # Print key findings
        if results['statistical_analysis']['paired_t_test']['significant']:
            improvement = results['statistical_analysis']['paired_t_test']['improvement']
            print(f"🎯 Key Finding: {improvement:.1f}% improvement detected")
        
        # Print top recommendations
        print("\n🔍 Top Recommendations:")
        for i, rec in enumerate(results['recommendations'][:3], 1):
            print(f"  {i}. {rec}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
    
    # List all available templates
    print(f"\n📋 Available Analysis Templates ({len(template_manager.templates)}):")
    for template_id, template in template_manager.templates.items():
        print(f"  • {template.name} - {template.description[:60]}...")
        print(f"    Target: {[org.value for org in template.target_organizations]}")
        print(f"    Analysis Type: {template.analysis_type.value}")
        print()

