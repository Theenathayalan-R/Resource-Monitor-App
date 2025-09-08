"""
Main Streamlit application for Platform Monitor
Enhanced with S3 storage monitoring and YAML-based configuration
"""
import streamlit as st
import logging
from datetime import datetime, timedelta, date
import os

# Initialize logging and performance monitoring
from logging_config import setup_logging, DatabaseError, KubernetesError, ValidationError
from performance import get_performance_monitor, start_background_monitoring
from config_loader import get_config

# Set up logging
logger = logging.getLogger(__name__)

# Load configuration
try:
    config = get_config()
    app_config = config.get('application', {})
    k8s_config = config.get('kubernetes', {})
    perf_config = config.get('performance', {})
    s3_config = config.get('s3', {})
    
    # Application settings
    PAGE_TITLE = app_config.get('title', 'Platform Monitor')
    PAGE_ICON = app_config.get('icon', '🔥')
    LAYOUT = app_config.get('layout', 'wide')
    REFRESH_INTERVAL = app_config.get('refresh_interval', 30)
    
    # Feature flags
    FEATURES = app_config.get('features', {})
    KUBERNETES_MONITORING = FEATURES.get('kubernetes_monitoring', True)
    S3_MONITORING = FEATURES.get('s3_monitoring', False)
    PERFORMANCE_METRICS = FEATURES.get('performance_metrics', True)
    
    # Global settings (with fallbacks)
    VIEW_MODES = config.get('view_modes', ['Current Status', 'Historical Analysis', 'Pod Timeline', 'Export Data'])
    TIME_RANGES = config.get('time_ranges', [1, 2, 6, 12, 24, 48, 72])
    EXPORT_FORMATS = config.get('export_formats', ['JSON', 'CSV'])
    
    # Kubernetes settings  
    DEFAULT_API_SERVER = k8s_config.get('api_server', 'https://api.cluster.openshift.com:6443')
    DEFAULT_NAMESPACE = k8s_config.get('namespace', 'spark-dev')
    
    # Performance settings
    ENABLE_PERFORMANCE_MONITORING = perf_config.get('monitoring_enabled', False)
    PERFORMANCE_MONITORING_INTERVAL = perf_config.get('monitoring_interval', 10)
    
    # Data retention
    data_retention = config.get('data_retention', {})
    HISTORY_RETENTION_DAYS = data_retention.get('history_days', 7)
    
except Exception as e:
    logger.error(f"Error loading configuration: {e}")
    # Fallback to default values
    PAGE_TITLE = "Platform Monitor"
    PAGE_ICON = "🔥"
    LAYOUT = "wide"
    REFRESH_INTERVAL = 30
    VIEW_MODES = ['Current Status', 'Historical Analysis', 'Pod Timeline', 'Storage Monitor', 'Export Data']
    DEFAULT_API_SERVER = "https://api.cluster.openshift.com:6443"
    DEFAULT_NAMESPACE = "spark-dev"
    KUBERNETES_MONITORING = True
    S3_MONITORING = False
    PERFORMANCE_METRICS = True

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

# S3 monitoring imports (conditional)
if S3_MONITORING:
    try:
        # Try relative imports first (when run as module)
        try:
            from .s3_adapter import S3Adapter
            from .views.s3_views import S3Views
        except ImportError:
            # Fallback to direct imports (when run directly)
            from s3_adapter import S3Adapter  
            from views.s3_views import S3Views
        S3_IMPORTS_AVAILABLE = True
    except ImportError as e:
        logger.warning(f"S3 monitoring disabled due to import error: {e}")
        S3_IMPORTS_AVAILABLE = False
        S3_MONITORING = False
else:
    S3_IMPORTS_AVAILABLE = False

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

    # --- Sidebar ---
    
    # Define a function to determine the correct view mode
    def get_current_view_mode(token_available, demo_mode_active):
        # Initialize view_mode in session state if it doesn't exist
        if 'view_mode' not in st.session_state:
            st.session_state['view_mode'] = VIEW_MODES[0]

        current_mode = st.session_state['view_mode']
        
        # Logic to determine if a switch is needed
        if demo_mode_active and current_mode != "Current Status":
            return "Current Status"
        elif not demo_mode_active and not token_available and current_mode == "Current Status":
            return "Historical Analysis"
        
        return current_mode

    # --- Create all sidebar widgets to get their current values ---
    
    # View Mode section at the top
    st.sidebar.header("👁️ View Mode")
    # Initialize view_mode in session state if it doesn't exist
    if 'view_mode' not in st.session_state:
        st.session_state['view_mode'] = VIEW_MODES[0]
    
    view_mode = st.sidebar.selectbox("Select View", VIEW_MODES, key="view_mode")
    
    # Pod filter settings for Current Status view - moved above history settings
    st.sidebar.subheader("🔍 Pod Filters (Current Status)")
    pod_age_hours = st.sidebar.selectbox(
        "Show pods started in last:",
        options=[1, 2, 6, 12, 24, 48, 72, 168],  # 1h, 2h, 6h, 12h, 1d, 2d, 3d, 1w
        index=0,  # Default to 1 hour
        format_func=lambda x: f"{x} hours" if x < 24 else f"{x//24} days",
        help="Filter pods by their creation time to improve performance and focus on recent activity"
    )
    
    st.sidebar.header("📚 History Settings")
    retention_days = st.sidebar.slider("Data retention (days)", 1, 30, HISTORY_RETENTION_DAYS)

    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
    refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 10, 300, REFRESH_INTERVAL)

    demo_mode = st.sidebar.checkbox(
        "Use mock data (demo)", 
        value=os.getenv('DEMO_MODE', '').lower() == 'true', 
        help="Populate UI with realistic sample Spark driver/executor pods and metrics without requiring a cluster token."
    )
    
    # Store demo mode in session state for use by other components
    st.session_state['demo_mode'] = demo_mode

    # Configuration section
    st.sidebar.header("⚙️ Configuration")
    api_server_url = st.sidebar.text_input(
        "OpenShift API Server URL",
        value=DEFAULT_API_SERVER,
        help="Enter the OpenShift/Kubernetes API server URL",
        key="api_server_input"
    )
    namespace = st.sidebar.text_input(
        "Project/Namespace",
        value=DEFAULT_NAMESPACE,
        help="Enter the namespace where Spark applications are running",
        key="namespace_input"
    )
    manual_token = st.sidebar.text_input(
        "Paste token manually:",
        type="password",
        help="Paste your service account token here",
        key="token_input"
    )

    # --- Logic and Validation ---

    # Validate config inputs
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

    # Extract and validate token
    token = None
    try:
        if manual_token.strip():
            token = validate_token(manual_token.strip())
            st.sidebar.success("✅ Token loaded from manual input")
            logger.info("Token validated from source: manual_input")
    except Exception as e:
        st.sidebar.error(f"❌ Invalid manual token: {str(e)}")

    # Show helpful hints for view mode selection based on configuration
    if not token and not demo_mode and view_mode == "Current Status":
        st.sidebar.warning("⚠️ Current Status requires a token or demo mode. Switch to Historical Analysis or provide a token.")
    
    if demo_mode and view_mode == "Historical Analysis":
        st.sidebar.info("💡 Demo mode works best with Current Status view.")

    # Performance monitoring display at the bottom
    show_performance_sidebar()

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
                auto_refresh,
                pod_age_hours
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
            
        elif view_mode == "Storage Monitor" and S3_MONITORING and S3_IMPORTS_AVAILABLE:
            st.header("🗄️ S3 Storage Monitoring")
            
            # Initialize S3 adapter and views
            if 's3_adapter' not in st.session_state:
                try:
                    # Check if we should use mock mode (same as general demo mode)
                    s3_mock_mode = st.session_state.get('demo_mode', False)
                    st.session_state.s3_adapter = S3Adapter(mock_mode=s3_mock_mode)
                    logger.info(f"S3 adapter initialized (mock_mode: {s3_mock_mode})")
                except Exception as e:
                    logger.error(f"Failed to initialize S3 adapter: {e}")
                    st.error(f"❌ Failed to initialize S3 monitoring: {e}")
                    st.stop()
            
            if 's3_views' not in st.session_state:
                st.session_state.s3_views = S3Views(st.session_state.s3_adapter)
            
            s3_adapter = st.session_state.s3_adapter
            s3_views = st.session_state.s3_views
            
            # S3 monitoring controls
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write("Monitor S3 bucket utilization and storage metrics across configured buckets")
                if s3_adapter.mock_mode:
                    st.info("🧪 **Demo Mode**: Showing realistic mock S3 data for demonstration")
            with col2:
                if st.button("🔄 Refresh S3 Data"):
                    s3_adapter.clear_cache()
                    st.rerun()
            with col3:
                if st.button("📊 Generate New Mock Data") and s3_adapter.mock_mode:
                    # Reset mock data generator to get new random values
                    try:
                        from .s3_mock_data import S3MockData
                    except ImportError:
                        from s3_mock_data import S3MockData
                    s3_adapter.mock_generator = S3MockData()
                    s3_adapter.clear_cache()
                    st.rerun()
            
            # Render S3 monitoring views
            try:
                # Platform storage summary tiles
                s3_views.render_platform_storage_tiles()
                
                st.markdown("---")
                
                # Individual bucket tiles
                s3_views.render_bucket_utilization_tiles()
                
                st.markdown("---")
                
                # Storage utilization chart
                s3_views.render_storage_utilization_chart()
                
                st.markdown("---")
                
                # Bucket selector with detailed view
                s3_views.render_bucket_selector_details()
                
                st.markdown("---")
                
                # Detailed metrics table
                s3_views.render_bucket_details_table()
                
            except Exception as e:
                logger.error(f"Error rendering S3 views: {e}")
                st.error(f"❌ Error displaying S3 monitoring: {e}")
                
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
            st.subheader("🛠️ Database Maintenance")
            
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
