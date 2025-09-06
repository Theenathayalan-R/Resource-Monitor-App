"""
Historical Analysis view: aggregations, trends, and app summary
"""
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

from charts import create_application_summary_chart, create_historical_timeline_chart


def render_historical(namespace: str, history_manager, demo_mode: bool):
    st.header("📊 Historical Analysis")

    # Time range selection
    col1, col2 = st.columns(2)
    with col1:
        from config import TIME_RANGES
        hours_back = st.selectbox("Time Range", TIME_RANGES, index=3)
    with col2:
        app_filter = st.text_input("Filter by App Name (optional)")

    historical_df = history_manager.get_historical_data(namespace, hours_back, app_filter if app_filter else None)

    if not historical_df.empty:
        # Summary statistics
        st.subheader("Summary Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(historical_df))
        with col2:
            active_pods = historical_df[historical_df['is_active'] == 1]
            st.metric("Active Pods", len(active_pods))
        with col3:
            unique_apps = historical_df['app_name'].nunique()
            st.metric("Unique Applications", unique_apps)

        # Application overview (sorted by most recent activity)
        st.subheader("Application Overview")
        app_summary = historical_df.groupby('app_name').agg({
            'pod_name': 'count',
            'cpu_usage': 'mean',
            'memory_usage': 'mean',
            'is_active': 'sum',
            'timestamp': 'max'  # Most recent activity per app
        }).round(2)
        app_summary.columns = ['Total Pods', 'Avg CPU Usage', 'Avg Memory Usage (MiB)', 'Active Pods', 'Last Activity']
        
        # Sort by most recent activity (newest first)
        app_summary = app_summary.sort_values('Last Activity', ascending=False)
        
        # Format the timestamp column
        app_summary['Last Activity'] = pd.to_datetime(app_summary['Last Activity']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        st.dataframe(app_summary, use_container_width=True)

        # Recent Pod Activity (newest first)
        st.subheader("Recent Pod Activity")
        
        # Show the most recent pod records
        recent_pods = historical_df.head(20).copy()  # Already sorted by timestamp DESC from database
        
        if not recent_pods.empty:
            recent_pods['timestamp'] = pd.to_datetime(recent_pods['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Select columns to display
            display_columns = ['timestamp', 'app_name', 'pod_name', 'pod_type', 'status', 
                             'cpu_usage', 'memory_usage', 'cpu_limit', 'memory_limit']
            
            # Filter to only existing columns
            display_columns = [col for col in display_columns if col in recent_pods.columns]
            
            recent_display = recent_pods[display_columns].copy()
            recent_display.columns = ['Last Updated', 'Application', 'Pod Name', 'Type', 'Status',
                                    'CPU Usage', 'Memory (MiB)', 'CPU Limit', 'Memory Limit (MiB)'][:len(display_columns)]
            
            st.dataframe(recent_display, use_container_width=True)

        # Resource usage trends
        st.subheader("Resource Usage Trends")
        fig = create_application_summary_chart(historical_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No historical data found for the selected time range.")


def render_timeline(namespace: str, history_manager):
    st.header("⏱️ Pod Timeline")

    # Get all pod names from history via HistoryManager for pooled access
    pod_names_list = history_manager.list_pod_names(namespace)
    pod_names = pd.DataFrame({'pod_name': pod_names_list}) if pod_names_list else pd.DataFrame(columns=['pod_name'])

    if not pod_names.empty:
        selected_pod = st.selectbox("Select Pod for Timeline", pod_names['pod_name'].tolist())

        if selected_pod:
            pod_df, events_df = history_manager.get_pod_timeline(namespace, selected_pod)

            if not pod_df.empty:
                # Timeline chart
                fig = create_historical_timeline_chart(pod_df, selected_pod)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

                # Pod events
                if not events_df.empty:
                    st.subheader("Pod Events")
                    st.dataframe(events_df, use_container_width=True)

                # Pod statistics
                st.subheader("Pod Statistics")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Records", len(pod_df))
                with col2:
                    avg_cpu = pod_df['cpu_usage'].mean()
                    st.metric("Avg CPU Usage", f"{avg_cpu:.2f}")
                with col3:
                    avg_mem = pod_df['memory_usage'].mean()
                    st.metric("Avg Memory Usage", f"{avg_mem:.0f} MiB")
            else:
                st.info(f"No timeline data found for pod: {selected_pod}")
    else:
        st.info("No pods found in historical data.")
