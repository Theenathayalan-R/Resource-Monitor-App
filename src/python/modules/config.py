"""
Configuration settings for Spark Pod Resource Monitor
Now loads from environment-specific YAML/JSON configuration files
"""
import os
import logging
from pathlib import Path
from config_loader import get_config, get_environment
from logging_config import ConfigurationError, setup_logging

# Load environment-specific configuration
config = get_config()

# Initialize logging with environment-specific settings
LOG_LEVEL = config.get('logging', {}).get('level', 'INFO')
LOG_FILE = config.get('logging', {}).get('file', 'logs/spark_monitor.log')
setup_logging(LOG_LEVEL, LOG_FILE)

logger = logging.getLogger(__name__)

# Database settings from config
db_config = config.get('database', {})
DB_TYPE = db_config.get('type', 'sqlite').lower()

if DB_TYPE == 'sqlite':
    DB_PATH = db_config.get('sqlite', {}).get('path', 'spark_pods_history.db')
    MAX_DB_CONNECTIONS = db_config.get('sqlite', {}).get('max_connections', 5)
elif DB_TYPE == 'oracle':
    ORACLE_CONFIG = db_config.get('oracle', {})
    MAX_DB_CONNECTIONS = ORACLE_CONFIG.get('max_connections', 10)
else:
    raise ConfigurationError(f"Unsupported database type: {DB_TYPE}")

# Data retention settings
retention_config = config.get('data_retention', {})
HISTORY_RETENTION_DAYS = retention_config.get('history_days', 7)

# Validate retention days
if not 1 <= HISTORY_RETENTION_DAYS <= 365:
    raise ConfigurationError(f"HISTORY_RETENTION_DAYS must be between 1 and 365, got {HISTORY_RETENTION_DAYS}")

# Kubernetes settings from config
k8s_config = config.get('kubernetes', {})
DEFAULT_API_SERVER = k8s_config.get('api_server', "https://api.your-cluster.openshift.com:6443")
DEFAULT_NAMESPACE = k8s_config.get('namespace', "spark-applications")
TLS_VERIFY = k8s_config.get('tls_verify', True)

# Application settings from config
app_config = config.get('application', {})
DEFAULT_REFRESH_INTERVAL = app_config.get('refresh_interval', 30)
PAGE_TITLE = app_config.get('title', 'Spark Pod Resource Monitor')
PAGE_ICON = app_config.get('icon', '🔥')
LAYOUT = app_config.get('layout', 'wide')

# Validate refresh interval
if not 10 <= DEFAULT_REFRESH_INTERVAL <= 3600:
    raise ConfigurationError(f"DEFAULT_REFRESH_INTERVAL must be between 10 and 3600, got {DEFAULT_REFRESH_INTERVAL}")

# Performance settings from config
perf_config = config.get('performance', {})
ENABLE_PERFORMANCE_MONITORING = perf_config.get('monitoring_enabled', True)
PERFORMANCE_MONITORING_INTERVAL = perf_config.get('monitoring_interval', 10)

# Performance thresholds from config
thresholds = perf_config.get('thresholds', {})
PERFORMANCE_THRESHOLDS = {
    'cpu_warning': thresholds.get('cpu_warning', 70.0),
    'cpu_critical': thresholds.get('cpu_critical', 90.0),
    'memory_warning': thresholds.get('memory_warning', 75.0),
    'memory_critical': thresholds.get('memory_critical', 90.0),
    'response_time_warning': thresholds.get('response_time_warning', 2000.0),
    'response_time_critical': thresholds.get('response_time_critical', 5000.0)
}

# Global settings from config
VIEW_MODES = config.get('view_modes', ["Current Status", "Historical Analysis", "Pod Timeline", "Export Data"])
TIME_RANGES = config.get('time_ranges', [1, 2, 6, 12, 24, 48, 72])
EXPORT_FORMATS = config.get('export_formats', ["JSON", "CSV"])

# Log configuration summary
environment = get_environment()
logger.info(f"Configuration loaded successfully for environment: {environment}")
logger.info(f"Database type: {DB_TYPE}")
logger.info(f"API server: {DEFAULT_API_SERVER}")
logger.info(f"Namespace: {DEFAULT_NAMESPACE}")
logger.info(f"Performance monitoring: {'enabled' if ENABLE_PERFORMANCE_MONITORING else 'disabled'}")

# Export configuration for use by other modules
def get_database_config():
    """Get database configuration based on type"""
    if DB_TYPE == 'sqlite':
        return {
            'type': 'sqlite',
            'path': DB_PATH,
            'max_connections': MAX_DB_CONNECTIONS
        }
    elif DB_TYPE == 'oracle':
        return {
            'type': 'oracle',
            'config': ORACLE_CONFIG,
            'max_connections': MAX_DB_CONNECTIONS
        }
    else:
        raise ConfigurationError(f"Unsupported database type: {DB_TYPE}")

def get_kubernetes_config():
    """Get Kubernetes configuration"""
    return {
        'api_server': DEFAULT_API_SERVER,
        'namespace': DEFAULT_NAMESPACE,
        'tls_verify': TLS_VERIFY,
        'token_file': k8s_config.get('token_file'),
        'token': k8s_config.get('token')  # From environment override
    }
