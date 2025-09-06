"""
Main Streamlit application for Spark Pod Resource Monitor
"""
import streamlit as st
import pandas as pd
import yaml
import sqlite3
import time
from datetime import datetime, timedelta, date

# Page config
from .config import (
    PAGE_ICON,
    PAGE_TITLE,
    HISTORY_RETENTION_DAYS,
    DEFAULT_API_SERVER,
    DEFAULT_NAMESPACE,
    DEFAULT_REFRESH_INTERVAL,
    VIEW_MODES,
    TIME_RANGES,
    EXPORT_FORMATS,
    LAYOUT,
)

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout=LAYOUT)

# Import our modules
from .database import HistoryManager
from .kubernetes_client import KubernetesClient
from .utils import (
    classify_spark_pods,
    get_pod_resources,
    extract_app_name,
    format_resource_value,
    calculate_utilization,
)
from .mock_data import generate_mock_pods, generate_mock_metrics
from .views.current_status import render_current_status
from .views.historical import render_historical, render_timeline


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

    # Option to use Streamlit secrets
    secret_token = None
    try:
        secret_token = st.secrets.get("KUBE_TOKEN", None)
    except Exception:
        secret_token = None
    use_secret = st.sidebar.checkbox("Use token from secrets", value=bool(secret_token))

    # Manual token input as alternative (masked)
    manual_token = st.sidebar.text_input(
        "Or paste token manually:",
        type="password",
        help="Paste your service account token here"
    )

    # History settings
    st.sidebar.header("History Settings")
    retention_days = st.sidebar.slider("Data retention (days)", 1, 30, HISTORY_RETENTION_DAYS)

    # Auto-refresh settings
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 10, 300, DEFAULT_REFRESH_INTERVAL)

    # Extract token before rendering view mode widget
    token = None

    if use_secret and secret_token:
        token = secret_token

    if not token and uploaded_token is not None:
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

    if not token and manual_token.strip():
        token = manual_token.strip()

    # Demo mode toggle (use mock data instead of connecting to a cluster)
    demo_mode = st.sidebar.checkbox("Use mock data (demo)", value=False, help="Populate UI with realistic sample Spark driver/executor pods and metrics without requiring a cluster token.")

    # Optional: seed demo data on demand
    if demo_mode and st.sidebar.button("Seed demo data now"):
        try:
            pods_seed, drivers_seed, executors_seed = generate_mock_pods(namespace, drivers=2, executors_per_driver=3)
            metrics_seed = generate_mock_metrics(pods_seed)
            batch_items = []
            active_pod_names = []
            for pod in pods_seed:
                app_name = extract_app_name(pod.metadata.name)
                pod_type = 'driver' if pod in drivers_seed else 'executor' if pod in executors_seed else 'unknown'
                if pod_type != 'unknown':
                    resources = get_pod_resources(pod)
                    m = metrics_seed.get(pod.metadata.name, {'cpu_usage': 0.0, 'memory_usage': 0.0})
                    batch_items.append((
                        namespace, pod.metadata.name, pod_type, app_name, pod.status.phase,
                        resources['cpu_request'], resources['cpu_limit'], m['cpu_usage'],
                        resources['memory_request'], resources['memory_limit'], m['memory_usage'],
                        getattr(pod.spec, 'node_name', None), getattr(pod.metadata, 'creation_timestamp', None),
                        dict(pod.metadata.labels or {}), dict(pod.metadata.annotations or {}),
                        sum(getattr(cs, 'restart_count', 0) for cs in (getattr(pod.status, 'container_statuses', []) or []))
                    ))
                    active_pod_names.append(pod.metadata.name)
            if batch_items:
                history_manager.store_pod_data_batch(batch_items)
                history_manager.mark_pods_inactive(namespace, active_pod_names)
            st.sidebar.success("Demo data seeded.")
        except Exception as e:
            st.sidebar.error(f"Seeding failed: {e}")

    # Ensure view_mode exists in session state and adjust prior to widget creation
    if 'view_mode' not in st.session_state:
        st.session_state['view_mode'] = VIEW_MODES[0]
    if demo_mode and st.session_state['view_mode'] != "Current Status":
        st.session_state['view_mode'] = "Current Status"
    elif not demo_mode and not token and st.session_state['view_mode'] == "Current Status":
        st.session_state['view_mode'] = "Historical Analysis"

    # View mode selection (after session_state adjustment above)
    st.sidebar.selectbox("View Mode", VIEW_MODES, key="view_mode")
    view_mode = st.session_state['view_mode']

    # Route to views
    if view_mode == "Current Status":
        render_current_status(namespace, api_server_url, token, history_manager, demo_mode, refresh_interval, auto_refresh)
    elif view_mode == "Historical Analysis":
        # Seed demo data automatically if empty
        if demo_mode:
            try:
                recent = history_manager.get_historical_data(namespace, 1, None)
                if recent.empty:
                    pods_seed, drivers_seed, executors_seed = generate_mock_pods(namespace, drivers=2, executors_per_driver=3)
                    metrics_seed = generate_mock_metrics(pods_seed)
                    batch_items = []
                    active_pod_names = []
                    for pod in pods_seed:
                        app_name = extract_app_name(pod.metadata.name)
                        pod_type = 'driver' if pod in drivers_seed else 'executor' if pod in executors_seed else 'unknown'
                        if pod_type != 'unknown':
                            resources = get_pod_resources(pod)
                            m = metrics_seed.get(pod.metadata.name, {'cpu_usage': 0.0, 'memory_usage': 0.0})
                            batch_items.append((
                                namespace, pod.metadata.name, pod_type, app_name, pod.status.phase,
                                resources['cpu_request'], resources['cpu_limit'], m['cpu_usage'],
                                resources['memory_request'], resources['memory_limit'], m['memory_usage'],
                                getattr(pod.spec, 'node_name', None), getattr(pod.metadata, 'creation_timestamp', None),
                                dict(pod.metadata.labels or {}), dict(pod.metadata.annotations or {}),
                                sum(getattr(cs, 'restart_count', 0) for cs in (getattr(pod.status, 'container_statuses', []) or []))
                            ))
                            active_pod_names.append(pod.metadata.name)
                    if batch_items:
                        history_manager.store_pod_data_batch(batch_items)
                        history_manager.mark_pods_inactive(namespace, active_pod_names)
                        st.info("Demo mode: seeded sample data for Historical Analysis.")
            except Exception as e:
                st.warning(f"Demo data seeding skipped: {e}")
        render_historical(namespace, history_manager, demo_mode)
    elif view_mode == "Pod Timeline":
        render_timeline(namespace, history_manager)
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
                def _normalize_date(obj):
                    # Convert possible tuple/list or direct date/datetime to a date-like object
                    if isinstance(obj, (datetime, date)):
                        return obj
                    if isinstance(obj, (list, tuple)) and len(obj) > 0 and isinstance(obj[0], (datetime, date)):
                        return obj[0]
                    return None

                s_obj = _normalize_date(start_date)
                e_obj = _normalize_date(end_date)
                if not s_obj or not e_obj:
                    st.error("Invalid start or end date")
                else:
                    start_str = s_obj.strftime("%Y-%m-%d")
                    end_str = e_obj.strftime("%Y-%m-%d")

                    exported_data = history_manager.export_historical_data(
                        namespace, start_str, end_str, export_format.lower()
                    )

                    st.download_button(
                        label=f"Download {export_format}",
                        data=str(exported_data),
                        file_name=f"spark_pods_{start_str}_to_{end_str}.{export_format.lower()}",
                        mime="application/json" if export_format == "JSON" else "text/csv",
                    )

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
