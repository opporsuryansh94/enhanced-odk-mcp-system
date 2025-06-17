"""
Enhanced Dashboard and Visualization System for ODK MCP System.
Provides modern, interactive dashboards with advanced analytics and geospatial mapping.
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import logging
from dataclasses import dataclass, asdict
from enum import Enum

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from plotly.utils import PlotlyJSONEncoder
import folium
from folium import plugins
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

import sqlalchemy as sa
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS

# Database Models
Base = declarative_base()


class ChartType(Enum):
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    HISTOGRAM = "histogram"
    BOX = "box"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"
    SUNBURST = "sunburst"
    CHOROPLETH = "choropleth"
    SANKEY = "sankey"
    FUNNEL = "funnel"


class DashboardType(Enum):
    OVERVIEW = "overview"
    ANALYTICS = "analytics"
    GEOSPATIAL = "geospatial"
    REAL_TIME = "real_time"
    CUSTOM = "custom"


@dataclass
class VisualizationConfig:
    chart_type: str
    title: str
    data_source: str
    x_axis: str
    y_axis: str
    color_by: Optional[str] = None
    size_by: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    aggregation: Optional[str] = None
    time_range: Optional[Dict[str, str]] = None


class Dashboard(Base):
    __tablename__ = 'dashboards'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    project_id = Column(String)
    
    # Dashboard details
    name = Column(String, nullable=False)
    description = Column(Text)
    dashboard_type = Column(String, default=DashboardType.CUSTOM.value)
    
    # Layout and configuration
    layout_config = Column(JSON)
    widgets = Column(JSON, default=list)
    filters = Column(JSON, default=dict)
    
    # Sharing and permissions
    is_public = Column(Boolean, default=False)
    shared_with = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_viewed_at = Column(DateTime)


class Widget(Base):
    __tablename__ = 'widgets'
    
    id = Column(String, primary_key=True)
    dashboard_id = Column(String, nullable=False)
    
    # Widget details
    name = Column(String, nullable=False)
    widget_type = Column(String, nullable=False)  # chart, metric, table, map
    
    # Configuration
    config = Column(JSON, nullable=False)
    data_source = Column(String)
    query = Column(Text)
    
    # Layout
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=4)
    height = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DataSource(Base):
    __tablename__ = 'data_sources'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    
    # Source details
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # form_data, external_api, database
    connection_config = Column(JSON)
    
    # Schema
    schema_config = Column(JSON)
    last_sync_at = Column(DateTime)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VisualizationEngine:
    """
    Advanced visualization engine with support for multiple chart types and interactive features.
    """
    
    def __init__(self):
        """Initialize the visualization engine."""
        self.logger = logging.getLogger(__name__)
        
        # Set Plotly theme
        pio.templates.default = "plotly_white"
        
        # Color palettes
        self.color_palettes = {
            "default": px.colors.qualitative.Set3,
            "professional": ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#592E83"],
            "nature": ["#2D5016", "#A4AC86", "#656D4A", "#414833", "#333D29"],
            "ocean": ["#003f5c", "#2f4b7c", "#665191", "#a05195", "#d45087"],
            "sunset": ["#ff6b6b", "#feca57", "#48dbfb", "#ff9ff3", "#54a0ff"]
        }
    
    def create_bar_chart(
        self,
        data: pd.DataFrame,
        x: str,
        y: str,
        color: str = None,
        title: str = "Bar Chart",
        orientation: str = "v"
    ) -> Dict[str, Any]:
        """
        Create an interactive bar chart.
        
        Args:
            data: DataFrame containing the data.
            x: Column name for x-axis.
            y: Column name for y-axis.
            color: Column name for color grouping.
            title: Chart title.
            orientation: Chart orientation ('v' for vertical, 'h' for horizontal).
            
        Returns:
            Plotly figure as JSON.
        """
        try:
            fig = px.bar(
                data,
                x=x,
                y=y,
                color=color,
                title=title,
                orientation=orientation,
                color_discrete_sequence=self.color_palettes["professional"]
            )
            
            fig.update_layout(
                showlegend=True,
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Arial, sans-serif", size=12),
                title=dict(font=dict(size=16, color="#2c3e50")),
                xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
            )
            
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>%{y}<extra></extra>',
                marker_line_width=0
            )
            
            return json.loads(fig.to_json())
            
        except Exception as e:
            self.logger.error(f"Bar chart creation error: {str(e)}")
            return self._create_error_chart(str(e))
    
    def create_line_chart(
        self,
        data: pd.DataFrame,
        x: str,
        y: str,
        color: str = None,
        title: str = "Line Chart"
    ) -> Dict[str, Any]:
        """
        Create an interactive line chart.
        
        Args:
            data: DataFrame containing the data.
            x: Column name for x-axis.
            y: Column name for y-axis.
            color: Column name for color grouping.
            title: Chart title.
            
        Returns:
            Plotly figure as JSON.
        """
        try:
            fig = px.line(
                data,
                x=x,
                y=y,
                color=color,
                title=title,
                color_discrete_sequence=self.color_palettes["professional"]
            )
            
            fig.update_layout(
                showlegend=True,
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Arial, sans-serif", size=12),
                title=dict(font=dict(size=16, color="#2c3e50")),
                xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
            )
            
            fig.update_traces(
                mode='lines+markers',
                line=dict(width=3),
                marker=dict(size=6),
                hovertemplate='<b>%{x}</b><br>%{y}<extra></extra>'
            )
            
            return json.loads(fig.to_json())
            
        except Exception as e:
            self.logger.error(f"Line chart creation error: {str(e)}")
            return self._create_error_chart(str(e))
    
    def create_pie_chart(
        self,
        data: pd.DataFrame,
        values: str,
        names: str,
        title: str = "Pie Chart"
    ) -> Dict[str, Any]:
        """
        Create an interactive pie chart.
        
        Args:
            data: DataFrame containing the data.
            values: Column name for values.
            names: Column name for labels.
            title: Chart title.
            
        Returns:
            Plotly figure as JSON.
        """
        try:
            fig = px.pie(
                data,
                values=values,
                names=names,
                title=title,
                color_discrete_sequence=self.color_palettes["professional"]
            )
            
            fig.update_layout(
                showlegend=True,
                font=dict(family="Arial, sans-serif", size=12),
                title=dict(font=dict(size=16, color="#2c3e50")),
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            fig.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>%{value}<br>%{percent}<extra></extra>',
                marker=dict(line=dict(color='#FFFFFF', width=2))
            )
            
            return json.loads(fig.to_json())
            
        except Exception as e:
            self.logger.error(f"Pie chart creation error: {str(e)}")
            return self._create_error_chart(str(e))
    
    def create_scatter_plot(
        self,
        data: pd.DataFrame,
        x: str,
        y: str,
        color: str = None,
        size: str = None,
        title: str = "Scatter Plot"
    ) -> Dict[str, Any]:
        """
        Create an interactive scatter plot.
        
        Args:
            data: DataFrame containing the data.
            x: Column name for x-axis.
            y: Column name for y-axis.
            color: Column name for color grouping.
            size: Column name for marker size.
            title: Chart title.
            
        Returns:
            Plotly figure as JSON.
        """
        try:
            fig = px.scatter(
                data,
                x=x,
                y=y,
                color=color,
                size=size,
                title=title,
                color_discrete_sequence=self.color_palettes["professional"]
            )
            
            fig.update_layout(
                showlegend=True,
                hovermode='closest',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Arial, sans-serif", size=12),
                title=dict(font=dict(size=16, color="#2c3e50")),
                xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
            )
            
            fig.update_traces(
                marker=dict(line=dict(width=1, color='rgba(255,255,255,0.8)')),
                hovertemplate='<b>%{x}, %{y}</b><extra></extra>'
            )
            
            return json.loads(fig.to_json())
            
        except Exception as e:
            self.logger.error(f"Scatter plot creation error: {str(e)}")
            return self._create_error_chart(str(e))
    
    def create_heatmap(
        self,
        data: pd.DataFrame,
        x: str,
        y: str,
        z: str,
        title: str = "Heatmap"
    ) -> Dict[str, Any]:
        """
        Create an interactive heatmap.
        
        Args:
            data: DataFrame containing the data.
            x: Column name for x-axis.
            y: Column name for y-axis.
            z: Column name for values.
            title: Chart title.
            
        Returns:
            Plotly figure as JSON.
        """
        try:
            # Pivot data for heatmap
            pivot_data = data.pivot(index=y, columns=x, values=z)
            
            fig = go.Figure(data=go.Heatmap(
                z=pivot_data.values,
                x=pivot_data.columns,
                y=pivot_data.index,
                colorscale='Viridis',
                hoverongaps=False,
                hovertemplate='<b>%{x}, %{y}</b><br>Value: %{z}<extra></extra>'
            ))
            
            fig.update_layout(
                title=title,
                font=dict(family="Arial, sans-serif", size=12),
                title_font=dict(size=16, color="#2c3e50"),
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            return json.loads(fig.to_json())
            
        except Exception as e:
            self.logger.error(f"Heatmap creation error: {str(e)}")
            return self._create_error_chart(str(e))
    
    def create_box_plot(
        self,
        data: pd.DataFrame,
        x: str,
        y: str,
        color: str = None,
        title: str = "Box Plot"
    ) -> Dict[str, Any]:
        """
        Create an interactive box plot.
        
        Args:
            data: DataFrame containing the data.
            x: Column name for x-axis (categories).
            y: Column name for y-axis (values).
            color: Column name for color grouping.
            title: Chart title.
            
        Returns:
            Plotly figure as JSON.
        """
        try:
            fig = px.box(
                data,
                x=x,
                y=y,
                color=color,
                title=title,
                color_discrete_sequence=self.color_palettes["professional"]
            )
            
            fig.update_layout(
                showlegend=True,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Arial, sans-serif", size=12),
                title=dict(font=dict(size=16, color="#2c3e50")),
                xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
            )
            
            fig.update_traces(
                hovertemplate='<b>%{x}</b><br>Q1: %{q1}<br>Median: %{median}<br>Q3: %{q3}<extra></extra>'
            )
            
            return json.loads(fig.to_json())
            
        except Exception as e:
            self.logger.error(f"Box plot creation error: {str(e)}")
            return self._create_error_chart(str(e))
    
    def create_histogram(
        self,
        data: pd.DataFrame,
        x: str,
        color: str = None,
        title: str = "Histogram",
        bins: int = 30
    ) -> Dict[str, Any]:
        """
        Create an interactive histogram.
        
        Args:
            data: DataFrame containing the data.
            x: Column name for values.
            color: Column name for color grouping.
            title: Chart title.
            bins: Number of bins.
            
        Returns:
            Plotly figure as JSON.
        """
        try:
            fig = px.histogram(
                data,
                x=x,
                color=color,
                title=title,
                nbins=bins,
                color_discrete_sequence=self.color_palettes["professional"]
            )
            
            fig.update_layout(
                showlegend=True,
                bargap=0.1,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Arial, sans-serif", size=12),
                title=dict(font=dict(size=16, color="#2c3e50")),
                xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
            )
            
            fig.update_traces(
                hovertemplate='<b>Range: %{x}</b><br>Count: %{y}<extra></extra>',
                marker_line_width=1,
                marker_line_color='rgba(255,255,255,0.8)'
            )
            
            return json.loads(fig.to_json())
            
        except Exception as e:
            self.logger.error(f"Histogram creation error: {str(e)}")
            return self._create_error_chart(str(e))
    
    def create_treemap(
        self,
        data: pd.DataFrame,
        path: List[str],
        values: str,
        title: str = "Treemap"
    ) -> Dict[str, Any]:
        """
        Create an interactive treemap.
        
        Args:
            data: DataFrame containing the data.
            path: List of column names for hierarchy.
            values: Column name for values.
            title: Chart title.
            
        Returns:
            Plotly figure as JSON.
        """
        try:
            fig = px.treemap(
                data,
                path=path,
                values=values,
                title=title,
                color_discrete_sequence=self.color_palettes["professional"]
            )
            
            fig.update_layout(
                font=dict(family="Arial, sans-serif", size=12),
                title=dict(font=dict(size=16, color="#2c3e50")),
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            fig.update_traces(
                hovertemplate='<b>%{label}</b><br>Value: %{value}<br>%{percentParent} of %{parent}<extra></extra>',
                marker=dict(line=dict(width=2, color='white'))
            )
            
            return json.loads(fig.to_json())
            
        except Exception as e:
            self.logger.error(f"Treemap creation error: {str(e)}")
            return self._create_error_chart(str(e))
    
    def create_geospatial_map(
        self,
        data: pd.DataFrame,
        lat: str,
        lon: str,
        color: str = None,
        size: str = None,
        title: str = "Geospatial Map"
    ) -> str:
        """
        Create an interactive geospatial map using Folium.
        
        Args:
            data: DataFrame containing the data.
            lat: Column name for latitude.
            lon: Column name for longitude.
            color: Column name for color grouping.
            size: Column name for marker size.
            title: Map title.
            
        Returns:
            HTML string of the map.
        """
        try:
            # Calculate center point
            center_lat = data[lat].mean()
            center_lon = data[lon].mean()
            
            # Create map
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=10,
                tiles='OpenStreetMap'
            )
            
            # Add markers
            for idx, row in data.iterrows():
                # Determine marker color
                if color and color in row:
                    marker_color = self._get_marker_color(row[color])
                else:
                    marker_color = 'blue'
                
                # Determine marker size
                if size and size in row:
                    marker_size = max(5, min(20, int(row[size] / data[size].max() * 20)))
                else:
                    marker_size = 10
                
                # Create popup text
                popup_text = f"<b>Location</b><br>Lat: {row[lat]}<br>Lon: {row[lon]}"
                if color and color in row:
                    popup_text += f"<br>{color}: {row[color]}"
                if size and size in row:
                    popup_text += f"<br>{size}: {row[size]}"
                
                folium.CircleMarker(
                    location=[row[lat], row[lon]],
                    radius=marker_size,
                    popup=popup_text,
                    color='white',
                    weight=2,
                    fillColor=marker_color,
                    fillOpacity=0.7
                ).add_to(m)
            
            # Add title
            title_html = f'''
                <h3 align="center" style="font-size:16px; color:#2c3e50; margin-top:10px;">
                    <b>{title}</b>
                </h3>
            '''
            m.get_root().html.add_child(folium.Element(title_html))
            
            return m._repr_html_()
            
        except Exception as e:
            self.logger.error(f"Geospatial map creation error: {str(e)}")
            return f"<div>Error creating map: {str(e)}</div>"
    
    def create_statistical_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Create statistical summary of the data.
        
        Args:
            data: DataFrame to analyze.
            
        Returns:
            Statistical summary dictionary.
        """
        try:
            summary = {
                "basic_stats": {},
                "correlations": {},
                "distributions": {},
                "outliers": {}
            }
            
            # Basic statistics for numeric columns
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                col_data = data[col].dropna()
                summary["basic_stats"][col] = {
                    "count": len(col_data),
                    "mean": float(col_data.mean()),
                    "median": float(col_data.median()),
                    "std": float(col_data.std()),
                    "min": float(col_data.min()),
                    "max": float(col_data.max()),
                    "q25": float(col_data.quantile(0.25)),
                    "q75": float(col_data.quantile(0.75)),
                    "skewness": float(stats.skew(col_data)),
                    "kurtosis": float(stats.kurtosis(col_data))
                }
            
            # Correlation matrix
            if len(numeric_cols) > 1:
                corr_matrix = data[numeric_cols].corr()
                summary["correlations"] = corr_matrix.to_dict()
            
            # Distribution analysis
            for col in numeric_cols:
                col_data = data[col].dropna()
                # Normality test
                if len(col_data) > 3:
                    _, p_value = stats.normaltest(col_data)
                    summary["distributions"][col] = {
                        "is_normal": p_value > 0.05,
                        "normality_p_value": float(p_value)
                    }
            
            # Outlier detection using IQR method
            for col in numeric_cols:
                col_data = data[col].dropna()
                Q1 = col_data.quantile(0.25)
                Q3 = col_data.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outliers = col_data[(col_data < lower_bound) | (col_data > upper_bound)]
                summary["outliers"][col] = {
                    "count": len(outliers),
                    "percentage": (len(outliers) / len(col_data)) * 100,
                    "values": outliers.tolist()[:10]  # Limit to first 10 outliers
                }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Statistical summary error: {str(e)}")
            return {"error": str(e)}
    
    def _get_marker_color(self, value: Any) -> str:
        """Get marker color based on value."""
        color_map = {
            0: 'red',
            1: 'blue',
            2: 'green',
            3: 'purple',
            4: 'orange',
            5: 'darkred',
            6: 'lightred',
            7: 'beige',
            8: 'darkblue',
            9: 'darkgreen'
        }
        
        if isinstance(value, (int, float)):
            return color_map.get(int(value) % 10, 'blue')
        else:
            return color_map.get(hash(str(value)) % 10, 'blue')
    
    def _create_error_chart(self, error_message: str) -> Dict[str, Any]:
        """Create an error chart when visualization fails."""
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error: {error_message}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="red")
        )
        fig.update_layout(
            title="Visualization Error",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        return json.loads(fig.to_json())


class DashboardManager:
    """
    Dashboard management system for creating and managing interactive dashboards.
    """
    
    def __init__(self, database_url: str = "sqlite:///dashboard.db"):
        """
        Initialize the dashboard manager.
        
        Args:
            database_url: Database connection URL.
        """
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Initialize visualization engine
        self.viz_engine = VisualizationEngine()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize Flask app
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes for dashboard management."""
        
        @self.app.route('/api/dashboard/create', methods=['POST'])
        def create_dashboard():
            """Create a new dashboard."""
            try:
                data = request.get_json()
                
                dashboard_id = str(uuid.uuid4())
                dashboard = Dashboard(
                    id=dashboard_id,
                    user_id=data.get('user_id'),
                    project_id=data.get('project_id'),
                    name=data.get('name'),
                    description=data.get('description', ''),
                    dashboard_type=data.get('dashboard_type', DashboardType.CUSTOM.value),
                    layout_config=data.get('layout_config', {}),
                    widgets=data.get('widgets', [])
                )
                
                with self.SessionLocal() as db:
                    db.add(dashboard)
                    db.commit()
                
                return jsonify({
                    "status": "success",
                    "dashboard_id": dashboard_id
                })
                
            except Exception as e:
                self.logger.error(f"Dashboard creation error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/dashboard/<dashboard_id>')
        def get_dashboard(dashboard_id):
            """Get dashboard details."""
            try:
                with self.SessionLocal() as db:
                    dashboard = db.query(Dashboard).filter(
                        Dashboard.id == dashboard_id
                    ).first()
                    
                    if not dashboard:
                        return jsonify({
                            "status": "error",
                            "message": "Dashboard not found"
                        }), 404
                    
                    # Get widgets
                    widgets = db.query(Widget).filter(
                        Widget.dashboard_id == dashboard_id
                    ).all()
                    
                    dashboard_data = {
                        "id": dashboard.id,
                        "name": dashboard.name,
                        "description": dashboard.description,
                        "dashboard_type": dashboard.dashboard_type,
                        "layout_config": dashboard.layout_config,
                        "widgets": [
                            {
                                "id": w.id,
                                "name": w.name,
                                "widget_type": w.widget_type,
                                "config": w.config,
                                "position_x": w.position_x,
                                "position_y": w.position_y,
                                "width": w.width,
                                "height": w.height
                            }
                            for w in widgets
                        ],
                        "created_at": dashboard.created_at.isoformat(),
                        "updated_at": dashboard.updated_at.isoformat()
                    }
                    
                    return jsonify({
                        "status": "success",
                        "dashboard": dashboard_data
                    })
                    
            except Exception as e:
                self.logger.error(f"Dashboard retrieval error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/dashboard/<dashboard_id>/widget', methods=['POST'])
        def add_widget(dashboard_id):
            """Add a widget to a dashboard."""
            try:
                data = request.get_json()
                
                widget_id = str(uuid.uuid4())
                widget = Widget(
                    id=widget_id,
                    dashboard_id=dashboard_id,
                    name=data.get('name'),
                    widget_type=data.get('widget_type'),
                    config=data.get('config', {}),
                    data_source=data.get('data_source'),
                    query=data.get('query'),
                    position_x=data.get('position_x', 0),
                    position_y=data.get('position_y', 0),
                    width=data.get('width', 4),
                    height=data.get('height', 3)
                )
                
                with self.SessionLocal() as db:
                    db.add(widget)
                    db.commit()
                
                return jsonify({
                    "status": "success",
                    "widget_id": widget_id
                })
                
            except Exception as e:
                self.logger.error(f"Widget creation error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/visualization/generate', methods=['POST'])
        def generate_visualization():
            """Generate a visualization based on configuration."""
            try:
                data = request.get_json()
                chart_type = data.get('chart_type')
                chart_data = pd.DataFrame(data.get('data', []))
                config = data.get('config', {})
                
                if chart_data.empty:
                    return jsonify({
                        "status": "error",
                        "message": "No data provided"
                    }), 400
                
                # Generate visualization based on type
                if chart_type == ChartType.BAR.value:
                    chart = self.viz_engine.create_bar_chart(
                        chart_data,
                        x=config.get('x'),
                        y=config.get('y'),
                        color=config.get('color'),
                        title=config.get('title', 'Bar Chart')
                    )
                elif chart_type == ChartType.LINE.value:
                    chart = self.viz_engine.create_line_chart(
                        chart_data,
                        x=config.get('x'),
                        y=config.get('y'),
                        color=config.get('color'),
                        title=config.get('title', 'Line Chart')
                    )
                elif chart_type == ChartType.PIE.value:
                    chart = self.viz_engine.create_pie_chart(
                        chart_data,
                        values=config.get('values'),
                        names=config.get('names'),
                        title=config.get('title', 'Pie Chart')
                    )
                elif chart_type == ChartType.SCATTER.value:
                    chart = self.viz_engine.create_scatter_plot(
                        chart_data,
                        x=config.get('x'),
                        y=config.get('y'),
                        color=config.get('color'),
                        size=config.get('size'),
                        title=config.get('title', 'Scatter Plot')
                    )
                elif chart_type == ChartType.HEATMAP.value:
                    chart = self.viz_engine.create_heatmap(
                        chart_data,
                        x=config.get('x'),
                        y=config.get('y'),
                        z=config.get('z'),
                        title=config.get('title', 'Heatmap')
                    )
                elif chart_type == ChartType.BOX.value:
                    chart = self.viz_engine.create_box_plot(
                        chart_data,
                        x=config.get('x'),
                        y=config.get('y'),
                        color=config.get('color'),
                        title=config.get('title', 'Box Plot')
                    )
                elif chart_type == ChartType.HISTOGRAM.value:
                    chart = self.viz_engine.create_histogram(
                        chart_data,
                        x=config.get('x'),
                        color=config.get('color'),
                        title=config.get('title', 'Histogram'),
                        bins=config.get('bins', 30)
                    )
                elif chart_type == ChartType.TREEMAP.value:
                    chart = self.viz_engine.create_treemap(
                        chart_data,
                        path=config.get('path', []),
                        values=config.get('values'),
                        title=config.get('title', 'Treemap')
                    )
                else:
                    return jsonify({
                        "status": "error",
                        "message": f"Unsupported chart type: {chart_type}"
                    }), 400
                
                return jsonify({
                    "status": "success",
                    "chart": chart
                })
                
            except Exception as e:
                self.logger.error(f"Visualization generation error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/visualization/map', methods=['POST'])
        def generate_map():
            """Generate a geospatial map."""
            try:
                data = request.get_json()
                map_data = pd.DataFrame(data.get('data', []))
                config = data.get('config', {})
                
                if map_data.empty:
                    return jsonify({
                        "status": "error",
                        "message": "No data provided"
                    }), 400
                
                map_html = self.viz_engine.create_geospatial_map(
                    map_data,
                    lat=config.get('lat'),
                    lon=config.get('lon'),
                    color=config.get('color'),
                    size=config.get('size'),
                    title=config.get('title', 'Geospatial Map')
                )
                
                return jsonify({
                    "status": "success",
                    "map_html": map_html
                })
                
            except Exception as e:
                self.logger.error(f"Map generation error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
        
        @self.app.route('/api/analytics/summary', methods=['POST'])
        def generate_analytics_summary():
            """Generate statistical summary of data."""
            try:
                data = request.get_json()
                analysis_data = pd.DataFrame(data.get('data', []))
                
                if analysis_data.empty:
                    return jsonify({
                        "status": "error",
                        "message": "No data provided"
                    }), 400
                
                summary = self.viz_engine.create_statistical_summary(analysis_data)
                
                return jsonify({
                    "status": "success",
                    "summary": summary
                })
                
            except Exception as e:
                self.logger.error(f"Analytics summary error: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": str(e)
                }), 500
    
    def run(self, host='0.0.0.0', port=5003, debug=False):
        """Run the dashboard application."""
        self.app.run(host=host, port=port, debug=debug)


# Create global instances
visualization_engine = VisualizationEngine()
dashboard_manager = DashboardManager()

