"""
Main Streamlit application for Spark Pod Resource Monitor
"""
import streamlit as st
import pandas as pd
import yaml
import sqlite3
import time
from datetime import datetime, timedelta

# Import our modules
from .config import *
from .database import HistoryManager
from .kubernetes_client import KubernetesClient
from .utils import *
from .charts import *


def main():
    st.title(f"{PAGE_ICON} {PAGE_TITLE}")
    st.markdown("Monitor Spark driver and executor pods with persistent historical tracking")

    # Initialize history manager
    if 'history_manager' not in st.session_state:
        st.session_state.history_manager = HistoryManager()

    history_manager = st.session_state.history_manager

    # Sidebar configuration
    st.sidebar.header("Configuration")

    api_server_url = st.sidebar.text_input(
        "OpenShift API Server URL",
        value=DEFAULT_API_SERVER,
        help="Enter the OpenShift/Kubernetes API server URL"
    )

    namespace = st.sidebar.text_input(
        "Project/Namespace",
        value=DEFAULT_NAMESPACE,
        help="Enter the namespace where Spark applications are running"
    )

    # File uploader for kubeconfig token
    uploaded_token = st.sidebar.file_uploader(
        "Upload Kubeconfig Token File",
        type=['txt', 'yaml', 'yml'],
        help="Upload your kubeconfig file or token file"
    )

    # Manual token input as alternative
    manual_token = st.sidebar.text_area(
        "Or paste token manually:",
        height=100,
        help="Paste your service account token here"
    )

    # History settings
    st.sidebar.header("History Settings")
    retention_days = st.sidebar.slider("Data retention (days)", 1, 30, HISTORY_RETENTION_DAYS)

    # Auto-refresh settings
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 10, 300, DEFAULT_REFRESH_INTERVAL)

    # View mode selection
    view_mode = st.sidebar.selectbox("View Mode", VIEW_MODES)

    # Extract token
    token = None
    if uploaded_token is not None:
        try:
            content = uploaded_token.read().decode('utf-8')
            if uploaded_token.name.endswith('.txt'):
                token = content.strip()
            else:
                kubeconfig = yaml.safe_load(content)
                if 'users' in kubeconfig:
                    for user in kubeconfig['users']:
                        if 'user' in user and 'token' in user['user']:
                            token = user['user']['token']
                            break
        except Exception as e:
            st.sidebar.error(f"Error reading token file: {str(e)}")

    elif manual_token.strip():
        token = manual_token.strip()

    if not token and view_mode == "Current Status":
        st.warning("Please provide a valid kubeconfig token to connect to the cluster for real-time monitoring.")
        st.info("""
        To get your token:
        1. Login to OpenShift: `oc login`
        2. Get token: `oc whoami -t`
        3. Or create service account and get its token
        """)
        if view_mode != "Historical Analysis":
            return

    # Current Status Mode
    if view_mode == "Current Status":
        # Initialize Kubernetes client
        if 'k8s_client' not in st.session_state or st.sidebar.button("Reconnect"):
            with st.spinner("Connecting to cluster..."):
                try:
                    st.session_state.k8s_client = KubernetesClient(api_server_url, token)
                    st.success("Successfully connected to the cluster!")
                except Exception as e:
                    st.error(f"Failed to connect to the cluster: {str(e)}")
                    return

        k8s_client = st.session_state.k8s_client

        # Fetch and store current pods data
        with st.spinner("Fetching pods and storing history..."):
            try:
                pods = k8s_client.get_pods(namespace)
                drivers, executors = classify_spark_pods(pods)

                # Store current pod data in history
                active_pod_names = []
                for pod in pods:
                    app_name = extract_app_name(pod.metadata.name)
                    pod_type = 'driver' if pod in drivers else 'executor' if pod in executors else 'unknown'

                    if pod_type != 'unknown':
                        resources = get_pod_resources(pod)
                        metrics = k8s_client.get_pod_metrics(namespace, pod.metadata.name)

                        history_manager.store_pod_data(
                            namespace, pod, pod_type, app_name, resources, metrics
                        )
                        active_pod_names.append(pod.metadata.name)

                # Mark inactive pods
                history_manager.mark_pods_inactive(namespace, active_pod_names)

            except Exception as e:
                st.error(f"Error fetching pod data: {str(e)}")
                return

        # Display current status
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Pods", len(pods))
        with col2:
            st.metric("Driver Pods", len(drivers))
        with col3:
            st.metric("Executor Pods", len(executors))
        with col4:
            st.metric("Last Updated", datetime.now().strftime("%H:%M:%S"))

        # Database statistics
        db_stats = history_manager.get_database_stats()
        st.info(f"""
        **Database Statistics:**
        - Pod Records: {db_stats['total_records']:,}
        - Event Records: {db_stats['total_events']:,}
        - Date Range: {db_stats['date_range'][0] if db_stats['date_range'][0] else 'N/A'} to {db_stats['date_range'][1] if db_stats['date_range'][1] else 'N/A'}
        """)

        # Driver pods overview
        if drivers:
            st.header("Spark Driver Pods")

            driver_data = []
            for driver in drivers:
                resources = get_pod_resources(driver)
                metrics = k8s_client.get_pod_metrics(namespace, driver.metadata.name)

                driver_data.append({
                    'Driver Name': driver.metadata.name,
                    'Status': driver.status.phase,
                    'CPU Request': format_resource_value(resources['cpu_request'], 'cpu'),
                    'CPU Limit': format_resource_value(resources['cpu_limit'], 'cpu'),
                    'CPU Usage': format_resource_value(metrics['cpu_usage'], 'cpu'),
                    'Memory Request (MB)': format_resource_value(resources['memory_request'], 'memory'),
                    'Memory Limit (MB)': format_resource_value(resources['memory_limit'], 'memory'),
                    'Memory Usage (MB)': format_resource_value(metrics['memory_usage'], 'memory'),
                    'Created': driver.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S") if driver.metadata.creation_timestamp else "Unknown"
                })

            driver_df = pd.DataFrame(driver_data)
            st.dataframe(driver_df, use_container_width=True)

            # Driver selection for detailed view
            selected_driver = st.selectbox(
                "Select Driver for Detailed View",
                options=[d['Driver Name'] for d in driver_data],
                key="driver_select"
            )

            if selected_driver:
                selected_driver_obj = next(d for d in drivers if d.metadata.name == selected_driver)

                st.subheader(f"Driver Details: {selected_driver}")

                # Get detailed info
                resources = get_pod_resources(selected_driver_obj)
                metrics = k8s_client.get_pod_metrics(namespace, selected_driver)

                chart_data = {**resources, **metrics}

                # Create detailed chart
                fig = create_resource_chart(chart_data, f"Resource Utilization - {selected_driver}")
                st.plotly_chart(fig, use_container_width=True)

                # Find associated executors
                driver_app_name = extract_app_name(selected_driver)
                associated_executors = [e for e in executors if extract_app_name(e.metadata.name) == driver_app_name]

                if associated_executors:
                    st.subheader(f"Associated Executors ({len(associated_executors)})")

                    executor_data = []
                    for executor in associated_executors:
                        exec_resources = get_pod_resources(executor)
                        exec_metrics = k8s_client.get_pod_metrics(namespace, executor.metadata.name)

                        executor_data.append({
                            'Executor Name': executor.metadata.name,
                            'Status': executor.status.phase,
                            'CPU Usage': format_resource_value(exec_metrics['cpu_usage'], 'cpu'),
                            'CPU Request': format_resource_value(exec_resources['cpu_request'], 'cpu'),
                            'CPU Limit': format_resource_value(exec_resources['cpu_limit'], 'cpu'),
                            'Memory Usage (MB)': format_resource_value(exec_metrics['memory_usage'], 'memory'),
                            'Memory Request (MB)': format_resource_value(exec_resources['memory_request'], 'memory'),
                            'Memory Limit (MB)': format_resource_value(exec_resources['memory_limit'], 'memory'),
                            'CPU Utilization %': f"{calculate_utilization(exec_metrics['cpu_usage'], exec_resources['cpu_limit']):.1f}%",
                            'Memory Utilization %': f"{calculate_utilization(exec_metrics['memory_usage'], exec_resources['memory_limit'], 1):.1f}%"
                        })

                    executor_df = pd.DataFrame(executor_data)
                    st.dataframe(executor_df, use_container_width=True)

        else:
            st.info("No Spark driver pods found in the specified namespace.")

    # Auto-refresh for current status mode
    if view_mode == "Current Status" and auto_refresh:
        time.sleep(refresh_interval)
        st.experimental_rerun()

    # Historical Analysis Mode
    elif view_mode == "Historical Analysis":
        st.header("📊 Historical Analysis")

        # Time range selection
        col1, col2 = st.columns(2)
        with col1:
            hours_back = st.selectbox("Time Range", TIME_RANGES, index=3)
        with col2:
            app_filter = st.text_input("Filter by App Name (optional)")

        # Get historical data
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

            # Application overview
            st.subheader("Application Overview")
            app_summary = historical_df.groupby('app_name').agg({
                'pod_name': 'count',
                'cpu_usage': 'mean',
                'memory_usage': 'mean',
                'is_active': 'sum'
            }).round(2)
            app_summary.columns = ['Total Pods', 'Avg CPU Usage', 'Avg Memory Usage', 'Active Pods']
            st.dataframe(app_summary, use_container_width=True)

            # Resource usage trends
            st.subheader("Resource Usage Trends")
            fig = create_application_summary_chart(historical_df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data found for the selected time range.")

    # Pod Timeline Mode
    elif view_mode == "Pod Timeline":
        st.header("⏱️ Pod Timeline")

        # Get all pod names from history
        conn = sqlite3.connect(history_manager.db_path)
        pod_names = pd.read_sql_query("SELECT DISTINCT pod_name FROM pod_history ORDER BY pod_name", conn)
        conn.close()

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
                        st.metric("Avg Memory Usage", f"{avg_mem:.0f} MB")
                else:
                    st.info(f"No timeline data found for pod: {selected_pod}")
        else:
            st.info("No pods found in historical data.")

    # Export Data Mode
    elif view_mode == "Export Data":
        st.header("📤 Export Data")

        # Export options
        col1, col2 = st.columns(2)
        with col1:
            export_format = st.selectbox("Export Format", EXPORT_FORMATS)
        with col2:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
            end_date = st.date_input("End Date", datetime.now())

        if st.button("Export Data"):
            with st.spinner("Exporting data..."):
                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")

                exported_data = history_manager.export_historical_data(
                    namespace, start_str, end_str, export_format.lower()
                )

                if export_format == "JSON":
                    st.download_button(
                        label="Download JSON",
                        data=exported_data,
                        file_name=f"spark_pods_{start_str}_to_{end_str}.json",
                        mime="application/json"
                    )
                else:
                    st.download_button(
                        label="Download CSV",
                        data=exported_data,
                        file_name=f"spark_pods_{start_str}_to_{end_str}.csv",
                        mime="text/csv"
                    )

                st.success("Data exported successfully!")

        # Database maintenance
        st.subheader("Database Maintenance")
        if st.button("Cleanup Old Data"):
            with st.spinner("Cleaning up old data..."):
                history_manager.cleanup_old_data(retention_days)
                st.success("Old data cleaned up successfully!")

        # Database statistics
        db_stats = history_manager.get_database_stats()
        st.info(f"Database contains {db_stats['total_records']:,} pod records and {db_stats['total_events']:,} event records")


if __name__ == "__main__":
    # Add CSS for better styling
    st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }

    .status-active {
        color: #28a745;
        font-weight: bold;
    }

    .status-terminated {
        color: #dc3545;
        font-weight: bold;
    }

    .timeline-event {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-left: 3px solid #1f77b4;
        background-color: #f8f9fa;
    }
    </style>
    """, unsafe_allow_html=True)

    main()
