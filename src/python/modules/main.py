"""
Main Streamlit application for Spark Pod Resource Monitor
"""
import streamlit as st
import pandas as pd
import yaml
import sqlite3
import time
import logging
from datetime import datetime, timedelta, date

# Initialize logging and performance monitoring
from logging_config import setup_logging, DatabaseError, KubernetesError, ValidationError
from performance import get_performance_monitor, start_background_monitoring

# Set up logging
logger = logging.getLogger(__name__)

# Page config
from config import (
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
    ENABLE_PERFORMANCE_MONITORING,
    PERFORMANCE_MONITORING_INTERVAL,
)

st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout=LAYOUT)

# Import our modules
from database import HistoryManager
from kubernetes_client import KubernetesClient
from utils import (
    classify_spark_pods,
    get_pod_resources,
    extract_app_name,
    format_resource_value,
    calculate_utilization,
)
from mock_data import generate_mock_pods, generate_mock_metrics
from views.current_status import render_current_status
from views.historical import render_historical, render_timeline
from validation import (
    validate_configuration,
    validate_namespace,
    validate_api_server_url,
    validate_token
)


def initialize_performance_monitoring():
    """Initialize performance monitoring if enabled"""
    if ENABLE_PERFORMANCE_MONITORING:
        try:
            start_background_monitoring(PERFORMANCE_MONITORING_INTERVAL)
            logger.info("Performance monitoring initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize performance monitoring: {str(e)}")


def show_performance_sidebar():
    """Show performance metrics in sidebar"""
    if not ENABLE_PERFORMANCE_MONITORING:
        return
        
    try:
        monitor = get_performance_monitor()
        current_metrics = monitor.get_current_metrics()
        
        if current_metrics:
            st.sidebar.subheader("📊 UI Performance")
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                st.metric("CPU", f"{current_metrics.cpu_percent:.1f}%")
                st.metric("DB Ops/s", f"{current_metrics.db_operations_per_sec:.1f}")
            with col2:
                st.metric("Memory", f"{current_metrics.memory_mb:.0f}MB")
                st.metric("API Calls/s", f"{current_metrics.k8s_api_calls_per_sec:.1f}")
            
            # Show performance warnings
            degradation = monitor.is_performance_degraded()
            if degradation.get('degraded'):
                issues = degradation.get('issues', {})
                for issue, value in issues.items():
                    if issue == 'high_cpu':
                        st.sidebar.warning(f"⚠️ High CPU usage: {value:.1f}%")
                    elif issue == 'high_memory':
                        st.sidebar.warning(f"⚠️ High memory usage: {value:.1f}%")
                    elif issue == 'slow_response':
                        st.sidebar.warning(f"⚠️ Slow response: {value:.0f}ms")
                        
    except Exception as e:
        logger.debug(f"Error displaying performance metrics: {str(e)}")


def show_error_message(error_type: str, error: Exception, show_details: bool = False):
    """Display user-friendly error messages"""
    if isinstance(error, ValidationError):
        st.error(f"❌ Configuration Error: {str(error)}")
    elif isinstance(error, DatabaseError):
        st.error(f"💾 Database Error: {str(error)}")
        if show_details:
            st.error("Please check database permissions and disk space.")
    elif isinstance(error, KubernetesError):
        st.error(f"☸️ Kubernetes Error: {str(error)}")
        if show_details:
            st.error("Please verify your API server URL, token, and network connectivity.")
    else:
        st.error(f"❌ {error_type}: {str(error)}")
        if show_details:
            st.error("Please check the application logs for more details.")


def main():
    # Initialize performance monitoring
    if 'performance_initialized' not in st.session_state:
        initialize_performance_monitoring()
        st.session_state.performance_initialized = True

    st.title(f"{PAGE_ICON} {PAGE_TITLE}")
    st.markdown("Monitor Spark driver and executor pods with persistent historical tracking")

    # Initialize history manager with error handling
    if 'history_manager' not in st.session_state:
        try:
            st.session_state.history_manager = HistoryManager()
            logger.info("History manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize history manager: {str(e)}", exc_info=True)
            show_error_message("Database Initialization Failed", e, show_details=True)
            st.stop()

    history_manager = st.session_state.history_manager

    # Sidebar configuration with validation
    st.sidebar.header("⚙️ Configuration")

    # API Server URL with validation
    api_server_url = st.sidebar.text_input(
        "OpenShift API Server URL",
        value=DEFAULT_API_SERVER,
        help="Enter the OpenShift/Kubernetes API server URL"
    )

    # Namespace with validation
    namespace = st.sidebar.text_input(
        "Project/Namespace",
        value=DEFAULT_NAMESPACE,
        help="Enter the namespace where Spark applications are running"
    )

    # Validate inputs immediately
    config_errors = []
    validated_config = {}
    
    try:
        if api_server_url.strip():
            validated_config['api_server_url'] = validate_api_server_url(api_server_url)
    except Exception as e:
        config_errors.append(f"API Server URL: {str(e)}")

    try:
        if namespace.strip():
            validated_config['namespace'] = validate_namespace(namespace)
    except Exception as e:
        config_errors.append(f"Namespace: {str(e)}")

    if config_errors:
        for error in config_errors:
            st.sidebar.error(f"❌ {error}")

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
        if secret_token:
            logger.info("Token loaded from Streamlit secrets")
    except Exception as e:
        logger.debug(f"No token found in secrets: {str(e)}")
        secret_token = None
        
    use_secret = st.sidebar.checkbox("Use token from secrets", value=bool(secret_token))

    # Manual token input as alternative (masked)
    manual_token = st.sidebar.text_input(
        "Or paste token manually:",
        type="password",
        help="Paste your service account token here"
    )

    # History settings with validation
    st.sidebar.header("📚 History Settings")
    retention_days = st.sidebar.slider("Data retention (days)", 1, 30, HISTORY_RETENTION_DAYS)

    # Auto-refresh settings with validation
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 10, 300, DEFAULT_REFRESH_INTERVAL)

    # Performance monitoring display
    show_performance_sidebar()

    # Extract and validate token
    token = None
    token_source = None

    try:
        if use_secret and secret_token:
            token = validate_token(secret_token)
            token_source = "secrets"

        if not token and uploaded_token is not None:
            try:
                content = uploaded_token.read().decode('utf-8')
                if uploaded_token.name.endswith('.txt'):
                    token = validate_token(content.strip())
                    token_source = "uploaded_file"
                else:
                    kubeconfig = yaml.safe_load(content)
                    if 'users' in kubeconfig:
                        for user in kubeconfig['users']:
                            if 'user' in user and 'token' in user['user']:
                                token = validate_token(user['user']['token'])
                                token_source = "kubeconfig"
                                break
                if not token:
                    st.sidebar.error("❌ No valid token found in uploaded file")
            except Exception as e:
                logger.error(f"Error reading token file: {str(e)}", exc_info=True)
                st.sidebar.error(f"❌ Error reading token file: {str(e)}")

        if not token and manual_token.strip():
            try:
                token = validate_token(manual_token.strip())
                token_source = "manual_input"
            except Exception as e:
                st.sidebar.error(f"❌ Invalid manual token: {str(e)}")

        if token and token_source:
            st.sidebar.success(f"✅ Token loaded from {token_source}")
            logger.info(f"Token validated from source: {token_source}")

    except Exception as e:
        logger.error(f"Token validation error: {str(e)}", exc_info=True)
        st.sidebar.error(f"❌ Token validation failed: {str(e)}")

    # Demo mode toggle
    demo_mode = st.sidebar.checkbox(
        "Use mock data (demo)", 
        value=False, 
        help="Populate UI with realistic sample Spark driver/executor pods and metrics without requiring a cluster token."
    )

    # Optional: seed demo data on demand
    if demo_mode and st.sidebar.button("Seed demo data now"):
        try:
            with st.spinner("Seeding demo data..."):
                pods_seed, drivers_seed, executors_seed = generate_mock_pods(
                    validated_config.get('namespace', namespace), drivers=2, executors_per_driver=3
                )
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
                            validated_config.get('namespace', namespace), pod.metadata.name, pod_type, app_name, 
                            pod.status.phase, resources['cpu_request'], resources['cpu_limit'], m['cpu_usage'],
                            resources['memory_request'], resources['memory_limit'], m['memory_usage'],
                            getattr(pod.spec, 'node_name', None), getattr(pod.metadata, 'creation_timestamp', None),
                            dict(pod.metadata.labels or {}), dict(pod.metadata.annotations or {}),
                            sum(getattr(cs, 'restart_count', 0) for cs in (getattr(pod.status, 'container_statuses', []) or []))
                        ))
                        active_pod_names.append(pod.metadata.name)
                
                if batch_items:
                    history_manager.store_pod_data_batch(batch_items)
                    history_manager.mark_pods_inactive(validated_config.get('namespace', namespace), active_pod_names)
                
                st.sidebar.success("✅ Demo data seeded successfully!")
                logger.info(f"Demo data seeded: {len(batch_items)} pods")
                
        except Exception as e:
            logger.error(f"Demo data seeding failed: {str(e)}", exc_info=True)
            st.sidebar.error(f"❌ Demo data seeding failed: {str(e)}")

    # Ensure view_mode exists in session state and adjust prior to widget creation
    if 'view_mode' not in st.session_state:
        st.session_state['view_mode'] = VIEW_MODES[0]
    
    # Auto-adjust view mode based on available data
    if demo_mode and st.session_state['view_mode'] != "Current Status":
        st.session_state['view_mode'] = "Current Status"
    elif not demo_mode and not token and st.session_state['view_mode'] == "Current Status":
        st.session_state['view_mode'] = "Historical Analysis"

    # View mode selection
    st.sidebar.header("👁️ View Mode")
    st.sidebar.selectbox("Select View", VIEW_MODES, key="view_mode")
    view_mode = st.session_state['view_mode']
    # Route to views with comprehensive error handling
    try:
        if view_mode == "Current Status":
            render_current_status(
                validated_config.get('namespace', namespace), 
                validated_config.get('api_server_url', api_server_url), 
                token, 
                history_manager, 
                demo_mode, 
                refresh_interval, 
                auto_refresh
            )
        elif view_mode == "Historical Analysis":
            # Seed demo data automatically if empty and in demo mode
            if demo_mode:
                try:
                    recent = history_manager.get_historical_data(
                        validated_config.get('namespace', namespace), 1, None
                    )
                    if recent.empty:
                        pods_seed, drivers_seed, executors_seed = generate_mock_pods(
                            validated_config.get('namespace', namespace), drivers=2, executors_per_driver=3
                        )
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
                                    validated_config.get('namespace', namespace), pod.metadata.name, pod_type, app_name, 
                                    pod.status.phase, resources['cpu_request'], resources['cpu_limit'], m['cpu_usage'],
                                    resources['memory_request'], resources['memory_limit'], m['memory_usage'],
                                    getattr(pod.spec, 'node_name', None), getattr(pod.metadata, 'creation_timestamp', None),
                                    dict(pod.metadata.labels or {}), dict(pod.metadata.annotations or {}),
                                    sum(getattr(cs, 'restart_count', 0) for cs in (getattr(pod.status, 'container_statuses', []) or []))
                                ))
                                active_pod_names.append(pod.metadata.name)
                        if batch_items:
                            history_manager.store_pod_data_batch(batch_items)
                            history_manager.mark_pods_inactive(
                                validated_config.get('namespace', namespace), active_pod_names
                            )
                            st.info("📊 Demo mode: seeded sample data for Historical Analysis.")
                except Exception as e:
                    logger.warning(f"Demo data seeding skipped: {str(e)}")
                    st.warning(f"⚠️ Demo data seeding skipped: {str(e)}")
            
            render_historical(validated_config.get('namespace', namespace), history_manager, demo_mode)
            
        elif view_mode == "Pod Timeline":
            render_timeline(validated_config.get('namespace', namespace), history_manager)
            
        elif view_mode == "Export Data":
            st.header("📤 Export Data")
            
            # Export options with validation
            col1, col2 = st.columns(2)
            with col1:
                export_format = st.selectbox("Export Format", EXPORT_FORMATS)
            with col2:
                start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
                end_date = st.date_input("End Date", datetime.now())

            if st.button("🔄 Export Data"):
                try:
                    with st.spinner("Exporting data..."):
                        def _normalize_date(obj):
                            if isinstance(obj, (datetime, date)):
                                return obj
                            if isinstance(obj, (list, tuple)) and len(obj) > 0 and isinstance(obj[0], (datetime, date)):
                                return obj[0]
                            return None

                        s_obj = _normalize_date(start_date)
                        e_obj = _normalize_date(end_date)
                        
                        if not s_obj or not e_obj:
                            st.error("❌ Invalid start or end date")
                        elif s_obj > e_obj:
                            st.error("❌ Start date must be before end date")
                        else:
                            start_str = s_obj.strftime("%Y-%m-%d")
                            end_str = e_obj.strftime("%Y-%m-%d")

                            exported_data = history_manager.export_historical_data(
                                validated_config.get('namespace', namespace), 
                                start_str, 
                                end_str, 
                                export_format.lower()
                            )

                            st.download_button(
                                label=f"💾 Download {export_format}",
                                data=str(exported_data),
                                file_name=f"spark_pods_{start_str}_to_{end_str}.{export_format.lower()}",
                                mime="application/json" if export_format == "JSON" else "text/csv",
                            )
                            
                            # Show export statistics
                            if export_format == "JSON":
                                import json
                                try:
                                    data = json.loads(exported_data)
                                    st.success(f"✅ Exported {len(data)} records successfully!")
                                except:
                                    st.success("✅ Data exported successfully!")
                            else:
                                lines = exported_data.count('\n')
                                st.success(f"✅ Exported {max(0, lines-1)} records successfully!")
                                
                except Exception as e:
                    logger.error(f"Export failed: {str(e)}", exc_info=True)
                    show_error_message("Export Failed", e, show_details=True)

            # Database maintenance with enhanced error handling
            st.subheader("� Database Maintenance")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧹 Cleanup Old Data"):
                    try:
                        with st.spinner("Cleaning up old data..."):
                            cleanup_result = history_manager.cleanup_old_data(retention_days)
                            st.success(f"✅ Cleanup completed! Removed {cleanup_result['history_records_deleted']} history records and {cleanup_result['events_deleted']} events.")
                            logger.info(f"Database cleanup completed: {cleanup_result}")
                    except Exception as e:
                        logger.error(f"Cleanup failed: {str(e)}", exc_info=True)
                        show_error_message("Cleanup Failed", e, show_details=True)
            
            with col2:
                if st.button("📊 Database Health Check"):
                    try:
                        with st.spinner("Checking database health..."):
                            stats = history_manager.get_database_stats()
                            
                            if stats.get('health_status') == 'healthy':
                                st.success("✅ Database is healthy!")
                            elif stats.get('health_status') == 'warning':
                                st.warning("⚠️ Database has warnings - check configuration")
                            else:
                                st.error("❌ Database health check failed")
                                
                    except Exception as e:
                        logger.error(f"Health check failed: {str(e)}", exc_info=True)
                        show_error_message("Health Check Failed", e, show_details=True)

            # Database statistics with enhanced display
            try:
                db_stats = history_manager.get_database_stats()
                
                st.subheader("📈 Database Statistics")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Records", f"{db_stats.get('total_records', 0):,}")
                with col2:
                    st.metric("Total Events", f"{db_stats.get('total_events', 0):,}")
                with col3:
                    st.metric("Active Pods", f"{db_stats.get('active_pods', 0):,}")
                with col4:
                    st.metric("Database Size", f"{db_stats.get('database_size_mb', 0):.1f} MB")
                
                # Show date range if available
                date_range = db_stats.get('date_range')
                if date_range and date_range[0] and date_range[1]:
                    st.info(f"📅 Data range: {date_range[0]} to {date_range[1]}")
                    
            except Exception as e:
                logger.error(f"Failed to get database stats: {str(e)}", exc_info=True)
                st.error("❌ Failed to retrieve database statistics")
                
    except Exception as e:
        logger.error(f"View rendering failed: {str(e)}", exc_info=True)
        show_error_message("View Rendering Failed", e, show_details=True)


if __name__ == "__main__":
    # Add enhanced CSS for better styling
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
    
    .performance-metric {
        background-color: #e8f4fd;
        padding: 0.25rem;
        border-radius: 0.25rem;
        font-size: 0.8rem;
    }
    
    .error-container {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .success-container {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.25rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

    try:
        main()
    except Exception as e:
        logger.critical(f"Application startup failed: {str(e)}", exc_info=True)
        st.error("❌ Application failed to start. Please check the logs for details.")
        st.error(f"Error: {str(e)}")
        
        # Show debug information in development
        if st.checkbox("Show debug information"):
            import traceback
            st.code(traceback.format_exc())
