"""
S3 Storage Views for Platform Monitoring UI

This module provides Streamlit UI components for displaying S3 storage
metrics, utilization tiles, and platform-wide storage summaries.
"""

try:
    import streamlit as st
    import plotly.express as px
    import plotly.graph_objects as go
    import pandas as pd
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    st = None
    px = None
    go = None
    pd = None

from typing import Dict, List, Optional
import logging
from datetime import datetime
try:
    from ..s3_adapter import S3Adapter
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from s3_adapter import S3Adapter

logger = logging.getLogger(__name__)


class S3Views:
    """
    UI components for S3 storage monitoring in Streamlit.
    
    Provides tiles, charts, and detailed views for S3 bucket utilization
    and platform storage metrics.
    """
    
    def __init__(self, s3_adapter: S3Adapter):
        """
        Initialize S3 views with adapter.
        
        Args:
            s3_adapter: S3Adapter instance for data access
        """
        self.s3_adapter = s3_adapter
        
        if not STREAMLIT_AVAILABLE:
            logger.error("Streamlit not available for S3 views")
    
    def render_platform_storage_tiles(self):
        """
        Render platform-wide storage summary tiles.
        
        Shows overall metrics across all S3 buckets including total storage,
        average utilization, and buckets over threshold.
        """
        if not STREAMLIT_AVAILABLE or not self.s3_adapter.is_enabled():
            st.warning("S3 monitoring is disabled or dependencies not available")
            return
        
        try:
            # Get platform summary
            summary = self.s3_adapter.get_platform_summary()
            
            # Create columns for tiles
            col1, col2, col3, col4 = st.columns(4)
            
            # Total Storage tile
            with col1:
                self._render_metric_tile(
                    title="Total S3 Storage",
                    value=f"{summary['total_size_gb']:.1f} GB",
                    delta=f"Quota: {summary['total_quota_gb']} GB",
                    help_text="Total storage used across all monitored S3 buckets"
                )
            
            # Average Utilization tile
            with col2:
                utilization_color = self._get_utilization_color(summary['average_utilization'])
                self._render_metric_tile(
                    title="Avg Utilization",
                    value=f"{summary['average_utilization']:.1f}%",
                    delta=f"{summary['total_buckets']} buckets",
                    delta_color=utilization_color,
                    help_text="Average utilization percentage across all buckets"
                )
            
            # Total Objects tile
            with col3:
                objects_formatted = self._format_number(summary['total_objects'])
                self._render_metric_tile(
                    title="Total Objects",
                    value=objects_formatted,
                    delta="files stored",
                    help_text="Total number of objects across all buckets"
                )
            
            # Alert Status tile
            with col4:
                alert_color = "red" if summary['buckets_over_threshold'] > 0 else "green"
                self._render_metric_tile(
                    title="Buckets Over Limit",
                    value=str(summary['buckets_over_threshold']),
                    delta=f"of {summary['total_buckets']} buckets",
                    delta_color=alert_color,
                    help_text="Number of buckets exceeding alert threshold"
                )
            
        except Exception as e:
            st.error(f"Error rendering platform storage tiles: {e}")
            logger.error(f"Error in render_platform_storage_tiles: {e}")
    
    def render_bucket_utilization_tiles(self):
        """
        Render individual bucket utilization tiles.
        
        Shows detailed metrics for each configured S3 bucket including
        usage percentage, file counts, and status indicators.
        """
        if not STREAMLIT_AVAILABLE or not self.s3_adapter.is_enabled():
            return
        
        try:
            bucket_metrics = self.s3_adapter.get_all_bucket_metrics()
            
            if not bucket_metrics:
                st.info("No S3 buckets configured for monitoring")
                return
            
            st.subheader("🗂️ S3 Bucket Utilization")
            
            # Create tiles for each bucket (3 per row)
            for i in range(0, len(bucket_metrics), 3):
                cols = st.columns(3)
                
                for j, col in enumerate(cols):
                    if i + j < len(bucket_metrics):
                        bucket = bucket_metrics[i + j]
                        with col:
                            self._render_bucket_tile(bucket)
            
        except Exception as e:
            st.error(f"Error rendering bucket utilization tiles: {e}")
            logger.error(f"Error in render_bucket_utilization_tiles: {e}")
    
    def render_storage_utilization_chart(self):
        """
        Render storage utilization chart showing all buckets.
        
        Creates a horizontal bar chart showing utilization percentage
        for each bucket with color coding based on thresholds.
        """
        if not STREAMLIT_AVAILABLE or not self.s3_adapter.is_enabled():
            return
        
        try:
            bucket_metrics = self.s3_adapter.get_all_bucket_metrics()
            
            if not bucket_metrics:
                return
            
            # Prepare data for chart
            chart_data = []
            for bucket in bucket_metrics:
                if bucket['quota_gb'] > 0:  # Only include buckets with quotas
                    chart_data.append({
                        'Bucket': bucket['display_name'],
                        'Utilization %': bucket['utilization_pct'],
                        'Status': bucket['status'],
                        'Alert Threshold': bucket['alert_threshold'],
                        'Size (GB)': bucket['total_size_gb'],
                        'Quota (GB)': bucket['quota_gb']
                    })
            
            if not chart_data:
                return
            
            df = pd.DataFrame(chart_data)
            
            # Create horizontal bar chart
            fig = px.bar(
                df,
                x='Utilization %',
                y='Bucket',
                orientation='h',
                title='S3 Bucket Storage Utilization',
                color='Status',
                color_discrete_map={
                    'healthy': '#28a745',
                    'warning': '#ffc107', 
                    'critical': '#dc3545',
                    'error': '#6c757d'
                },
                hover_data={
                    'Size (GB)': True,
                    'Quota (GB)': True,
                    'Alert Threshold': True,
                    'Status': False
                }
            )
            
            # Customize layout
            fig.update_layout(
                height=max(400, len(chart_data) * 60),
                xaxis_title="Utilization Percentage (%)",
                yaxis_title="S3 Buckets",
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            # Add threshold lines
            for _, bucket in df.iterrows():
                fig.add_vline(
                    x=bucket['Alert Threshold'],
                    line_dash="dash",
                    line_color="orange",
                    opacity=0.3
                )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering storage utilization chart: {e}")
            logger.error(f"Error in render_storage_utilization_chart: {e}")
    
    def render_bucket_details_table(self):
        """
        Render detailed table with all bucket metrics.
        
        Shows comprehensive information including storage usage,
        object counts, quotas, and last update timestamps.
        """
        if not STREAMLIT_AVAILABLE or not self.s3_adapter.is_enabled():
            return
        
        try:
            bucket_metrics = self.s3_adapter.get_all_bucket_metrics()
            
            if not bucket_metrics:
                return
            
            # Prepare data for table
            table_data = []
            for bucket in bucket_metrics:
                # Format last updated time
                try:
                    last_updated = datetime.fromisoformat(bucket['last_updated'].replace('Z', '+00:00'))
                    formatted_time = last_updated.strftime('%Y-%m-%d %H:%M:%S UTC')
                except:
                    formatted_time = "Unknown"
                
                table_data.append({
                    'Bucket Name': bucket['display_name'],
                    'Size (GB)': f"{bucket['total_size_gb']:.2f}",
                    'Objects': f"{bucket['object_count']:,}",
                    'Quota (GB)': f"{bucket['quota_gb']:,}",
                    'Utilization': f"{bucket['utilization_pct']:.1f}%",
                    'Threshold': f"{bucket['alert_threshold']}%",
                    'Status': bucket['status'].title(),
                    'Last Updated': formatted_time,
                    'Error': bucket.get('error', '') or ''
                })
            
            if table_data:
                df = pd.DataFrame(table_data)
                
                # Style the dataframe
                def style_status(val):
                    if val.lower() == 'critical':
                        return 'background-color: #ffebee; color: #c62828'
                    elif val.lower() == 'warning':
                        return 'background-color: #fff8e1; color: #f57f17'
                    elif val.lower() == 'healthy':
                        return 'background-color: #e8f5e8; color: #2e7d32'
                    elif val.lower() == 'error':
                        return 'background-color: #f5f5f5; color: #757575'
                    return ''
                
                styled_df = df.style.map(style_status, subset=['Status'])
                
                st.subheader("📊 Detailed S3 Bucket Metrics")
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
        except Exception as e:
            st.error(f"Error rendering bucket details table: {e}")
            logger.error(f"Error in render_bucket_details_table: {e}")
    
    def render_bucket_selector_details(self):
        """
        Render dropdown selector for bucket and show detailed information.
        
        Allows users to select a specific bucket from dropdown and displays
        comprehensive details including storage breakdown, object statistics,
        and historical trends.
        """
        if not STREAMLIT_AVAILABLE or not self.s3_adapter.is_enabled():
            return
        
        try:
            bucket_metrics = self.s3_adapter.get_all_bucket_metrics()
            
            if not bucket_metrics:
                st.info("No S3 buckets configured for monitoring")
                return
            
            st.subheader("🔍 Detailed Bucket Analysis")
            
            # Create dropdown for bucket selection
            bucket_options = {bucket['display_name']: bucket for bucket in bucket_metrics}
            bucket_names = list(bucket_options.keys())
            
            selected_bucket_name = st.selectbox(
                "Select a bucket to view detailed information:",
                bucket_names,
                help="Choose an S3 bucket to see comprehensive details and metrics"
            )
            
            if selected_bucket_name:
                selected_bucket = bucket_options[selected_bucket_name]
                self._render_detailed_bucket_view(selected_bucket)
                
        except Exception as e:
            st.error(f"Error rendering bucket selector: {e}")
            logger.error(f"Error in render_bucket_selector_details: {e}")
    
    def _render_detailed_bucket_view(self, bucket: Dict):
        """
        Render comprehensive detailed view for selected bucket.
        
        Args:
            bucket: Selected bucket metrics dictionary
        """
        try:
            # Header section with bucket name and status
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### 📦 {bucket['display_name']}")
                st.markdown(f"**Bucket Name:** `{bucket['bucket_name']}`")
                if bucket.get('endpoint_url'):
                    st.markdown(f"**Endpoint:** `{bucket['endpoint_url']}`")
            
            with col2:
                status_colors = {
                    'healthy': '🟢',
                    'warning': '🟡', 
                    'critical': '🔴',
                    'error': '❌'
                }
                status_icon = status_colors.get(bucket['status'], '⚪')
                st.markdown(f"### {status_icon} {bucket['status'].title()}")
            
            # Key metrics section
            st.markdown("#### 📊 Key Metrics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Storage Used",
                    f"{bucket['total_size_gb']:.2f} GB",
                    help="Total storage space currently used"
                )
            
            with col2:
                st.metric(
                    "Utilization",
                    f"{bucket['utilization_pct']:.1f}%",
                    delta=f"Threshold: {bucket['alert_threshold']}%",
                    delta_color="inverse" if bucket['utilization_pct'] > bucket['alert_threshold'] else "normal",
                    help="Current utilization percentage vs alert threshold"
                )
            
            with col3:
                st.metric(
                    "Object Count",
                    f"{bucket['object_count']:,}",
                    help="Total number of objects/files stored"
                )
            
            with col4:
                remaining_gb = bucket['quota_gb'] - bucket['total_size_gb']
                st.metric(
                    "Available Space",
                    f"{remaining_gb:.2f} GB",
                    delta=f"of {bucket['quota_gb']} GB quota",
                    help="Remaining storage space available"
                )
            
            # Visual progress bar
            st.markdown("#### 📈 Storage Utilization")
            progress_value = min(bucket['utilization_pct'] / 100.0, 1.0)
            st.progress(progress_value)
            
            # Color-coded status explanation
            if bucket['utilization_pct'] >= bucket['alert_threshold']:
                if bucket['utilization_pct'] >= 90:
                    st.error(f"⚠️ Critical: Storage is {bucket['utilization_pct']:.1f}% full (≥90%)")
                else:
                    st.warning(f"⚠️ Warning: Storage is {bucket['utilization_pct']:.1f}% full (≥{bucket['alert_threshold']}%)")
            else:
                st.success(f"✅ Healthy: Storage is {bucket['utilization_pct']:.1f}% full (<{bucket['alert_threshold']}%)")
            
            # Additional details section
            st.markdown("#### ℹ️ Additional Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Last updated info
                try:
                    last_updated = datetime.fromisoformat(bucket['last_updated'].replace('Z', '+00:00'))
                    formatted_time = last_updated.strftime('%Y-%m-%d %H:%M:%S UTC')
                    st.info(f"**Last Updated:** {formatted_time}")
                except:
                    st.info("**Last Updated:** Unknown")
                
                # Mock data indicator
                if bucket.get('mock_data'):
                    st.info("🎭 **Demo Mode:** This is simulated data for demonstration")
            
            with col2:
                # Error information if present
                if bucket.get('error'):
                    st.error(f"**Error:** {bucket['error']}")
                else:
                    st.success("**Status:** No errors detected")
                
                # Capacity calculation
                avg_object_size = bucket['total_size_gb'] * 1024 / bucket['object_count'] if bucket['object_count'] > 0 else 0
                st.info(f"**Avg Object Size:** {avg_object_size:.2f} MB")
            
            # Folder structure analysis for the selected bucket
            st.markdown("#### 📁 Folder Structure Analysis (3 Levels)")
            self._render_folder_structure_analysis(bucket)
                
        except Exception as e:
            st.error(f"Error rendering detailed bucket view: {e}")
            logger.error(f"Error in _render_detailed_bucket_view: {e}")
    
    def _render_folder_structure_analysis(self, bucket: Dict):
        """
        Render folder structure analysis for the selected bucket showing 3 levels of hierarchy.
        
        Args:
            bucket: Selected bucket metrics dictionary
        """
        try:
            bucket_name = bucket['bucket_name']
            
            # Get folder structure data from the adapter
            folder_structure = self.s3_adapter.get_bucket_folder_structure(bucket_name)
            
            if not folder_structure:
                st.info("No folder structure data available for this bucket")
                return
            
            # Create tabs for different levels
            tab1, tab2, tab3 = st.tabs(["📂 Level 1 (Root)", "📁 Level 2 (Subfolders)", "📄 Level 3 (Details)"])
            
            with tab1:
                st.markdown("**Root Folders**")
                # Create columns for root folder tiles
                if len(folder_structure) > 0:
                    cols = st.columns(min(3, len(folder_structure)))
                    for i, root_folder in enumerate(folder_structure):
                        col_idx = i % 3
                        with cols[col_idx]:
                            self._render_folder_tile(root_folder, level=1)
            
            with tab2:
                # Level 2 - Show subfolders for each root folder
                for root_folder in folder_structure:
                    if root_folder.get('subfolders'):
                        st.markdown(f"**📂 {root_folder['name']}** subfolders:")
                        
                        # Create expandable section for each root folder
                        with st.expander(f"View {root_folder['name']} subfolders ({len(root_folder['subfolders'])} folders)", expanded=False):
                            # Create columns for subfolder tiles
                            subfolders = root_folder['subfolders']
                            if subfolders:
                                cols = st.columns(min(2, len(subfolders)))
                                for j, subfolder in enumerate(subfolders):
                                    col_idx = j % 2
                                    with cols[col_idx]:
                                        self._render_folder_tile(subfolder, level=2)
            
            with tab3:
                # Level 3 - Show detailed breakdown
                st.markdown("**Detailed Folder Analysis (Level 3)**")
                
                for root_folder in folder_structure:
                    if root_folder.get('subfolders'):
                        st.markdown(f"### 📂 {root_folder['name']}")
                        
                        for subfolder in root_folder['subfolders']:
                            if subfolder.get('subfolders'):
                                st.markdown(f"#### 📁 {subfolder['name']}")
                                
                                # Create detailed table for level 3
                                level3_data = []
                                for sub_subfolder in subfolder['subfolders']:
                                    level3_data.append({
                                        'Folder': sub_subfolder['name'],
                                        'Path': sub_subfolder['path'],
                                        'Objects': f"{sub_subfolder['object_count']:,}",
                                        'Size (GB)': f"{sub_subfolder['size_gb']:.2f}",
                                        'Size %': f"{sub_subfolder['size_percentage']:.1f}%",
                                        'Avg File Size (MB)': f"{sub_subfolder.get('avg_file_size_mb', 0):.2f}",
                                        'Last Modified': sub_subfolder['last_modified'][:19].replace('T', ' ')
                                    })
                                
                                if level3_data:
                                    df = pd.DataFrame(level3_data)
                                    st.dataframe(df, use_container_width=True, hide_index=True)
                                
                                st.markdown("---")
            
            # Summary statistics
            st.markdown("#### 📊 Folder Summary Statistics")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_folders = len(folder_structure)
                total_subfolders = sum(len(f.get('subfolders', [])) for f in folder_structure)
                st.metric("Total Root Folders", total_folders)
            
            with col2:
                st.metric("Total Subfolders", total_subfolders)
            
            with col3:
                total_level3 = sum(
                    len(sf.get('subfolders', []))
                    for f in folder_structure
                    for sf in f.get('subfolders', [])
                )
                st.metric("Total Level 3 Folders", total_level3)
                
        except Exception as e:
            st.error(f"Error rendering folder structure analysis: {e}")
            logger.error(f"Error in _render_folder_structure_analysis: {e}")
    
    def _render_folder_tile(self, folder: Dict, level: int = 1):
        """
        Render individual folder tile with metrics.
        
        Args:
            folder: Folder data dictionary
            level: Folder hierarchy level (1, 2, or 3)
        """
        try:
            # Icon based on level
            icons = {1: "📂", 2: "📁", 3: "📄"}
            icon = icons.get(level, "📂")
            
            # Color based on size percentage
            size_pct = folder.get('size_percentage', 0)
            if size_pct > 20:
                color = "#e3f2fd"  # Blue
            elif size_pct > 10:
                color = "#f3e5f5"  # Purple
            elif size_pct > 5:
                color = "#e8f5e8"  # Green
            else:
                color = "#fafafa"  # Gray
            
            st.markdown(
                f"""
                <div style="
                    background-color: {color};
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #2196f3;
                    margin-bottom: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <h5 style="margin: 0; color: #333;">{icon} {folder['name']}</h5>
                    <p style="margin: 5px 0; color: #666; font-size: 14px;">
                        <strong>{folder.get('size_gb', 0):.2f} GB</strong> ({folder.get('size_percentage', 0):.1f}%)
                    </p>
                    <p style="margin: 0; color: #888; font-size: 12px;">
                        {folder.get('object_count', 0):,} objects
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        except Exception as e:
            st.error(f"Error rendering folder tile: {e}")
            logger.error(f"Error in _render_folder_tile: {e}")

    def _render_bucket_tile(self, bucket: Dict):
        """
        Render individual bucket utilization tile.
        
        Args:
            bucket: Bucket metrics dictionary
        """
        try:
            # Determine tile color based on status
            status_colors = {
                'healthy': '#e8f5e8',
                'warning': '#fff8e1',
                'critical': '#ffebee',
                'error': '#f5f5f5'
            }
            
            status_icons = {
                'healthy': '✅',
                'warning': '⚠️',
                'critical': '🔴',
                'error': '❌'
            }
            
            status = bucket['status']
            color = status_colors.get(status, '#f8f9fa')
            icon = status_icons.get(status, '📊')
            
            # Create tile container
            with st.container():
                st.markdown(
                    f"""
                    <div style="
                        background-color: {color};
                        padding: 20px;
                        border-radius: 10px;
                        border-left: 4px solid {'#28a745' if status == 'healthy' else '#ffc107' if status == 'warning' else '#dc3545' if status == 'critical' else '#6c757d'};
                        margin-bottom: 15px;
                    ">
                        <h4>{icon} {bucket['display_name']}</h4>
                        <div style="font-size: 24px; font-weight: bold; color: #333;">
                            {bucket['utilization_pct']:.1f}%
                        </div>
                        <div style="color: #666; font-size: 14px;">
                            {bucket['total_size_gb']:.1f} GB of {bucket['quota_gb']} GB
                        </div>
                        <div style="color: #666; font-size: 12px;">
                            {bucket['object_count']:,} objects • Threshold: {bucket['alert_threshold']}%
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Show error if present
                if bucket.get('error'):
                    st.error(f"Error: {bucket['error']}")
                    
        except Exception as e:
            st.error(f"Error rendering bucket tile: {e}")
            logger.error(f"Error in _render_bucket_tile: {e}")
    
    def _render_metric_tile(
        self, 
        title: str, 
        value: str, 
        delta: Optional[str] = None,
        delta_color: Optional[str] = None,
        help_text: Optional[str] = None
    ):
        """
        Render generic metric tile.
        
        Args:
            title: Tile title
            value: Main metric value
            delta: Additional information or delta value
            delta_color: Color for delta text
            help_text: Help text for tooltip
        """
        try:
            # Use Streamlit metric component
            st.metric(
                label=title,
                value=value,
                delta=delta,
                help=help_text
            )
            
        except Exception as e:
            st.error(f"Error rendering metric tile: {e}")
    
    def _get_utilization_color(self, utilization: float) -> str:
        """
        Get color based on utilization percentage.
        
        Args:
            utilization: Utilization percentage
            
        Returns:
            str: Color string for display
        """
        if utilization >= 90:
            return "red"
        elif utilization >= 75:
            return "orange"
        else:
            return "green"
    
    def _format_number(self, number: int) -> str:
        """
        Format large numbers with appropriate suffixes.
        
        Args:
            number: Number to format
            
        Returns:
            str: Formatted number string
        """
        if number >= 1_000_000:
            return f"{number / 1_000_000:.1f}M"
        elif number >= 1_000:
            return f"{number / 1_000:.1f}K"
        else:
            return str(number)
