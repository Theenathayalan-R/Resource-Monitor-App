"""
Configuration settings for Spark Pod Resource Monitor
"""
import os
import logging
from pathlib import Path
from logging_config import ConfigurationError, setup_logging

# Initialize logging first
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/spark_monitor.log')
setup_logging(LOG_LEVEL, LOG_FILE)

logger = logging.getLogger(__name__)

# Database settings
DB_PATH = os.getenv('DB_PATH', 'spark_pods_history.db')
HISTORY_RETENTION_DAYS = int(os.getenv('HISTORY_RETENTION_DAYS', '7'))

# Validate retention days
if not 1 <= HISTORY_RETENTION_DAYS <= 365:
    raise ConfigurationError(f"HISTORY_RETENTION_DAYS must be between 1 and 365, got {HISTORY_RETENTION_DAYS}")

# Default values
DEFAULT_API_SERVER = "https://api.your-cluster.openshift.com:6443"
DEFAULT_NAMESPACE = "spark-applications"
DEFAULT_REFRESH_INTERVAL = int(os.getenv('DEFAULT_REFRESH_INTERVAL', '30'))

# Validate refresh interval
if not 10 <= DEFAULT_REFRESH_INTERVAL <= 3600:
    raise ConfigurationError(f"DEFAULT_REFRESH_INTERVAL must be between 10 and 3600, got {DEFAULT_REFRESH_INTERVAL}")

# UI settings
PAGE_TITLE = "Spark Pod Resource Monitor"
PAGE_ICON = "🔥"
LAYOUT = "wide"

# Security settings
# Prefer secure TLS by default; allow opting out via env var (not recommended for prod)
TLS_VERIFY = os.getenv('TLS_VERIFY', 'true').lower() in ('1', 'true', 'yes')

# Performance settings
MAX_DB_CONNECTIONS = int(os.getenv('MAX_DB_CONNECTIONS', '5'))
PERFORMANCE_MONITORING_INTERVAL = int(os.getenv('PERFORMANCE_MONITORING_INTERVAL', '10'))
ENABLE_PERFORMANCE_MONITORING = os.getenv('ENABLE_PERFORMANCE_MONITORING', 'true').lower() in ('1', 'true', 'yes')

# View modes
VIEW_MODES = ["Current Status", "Historical Analysis", "Pod Timeline", "Export Data"]

# Time range options
TIME_RANGES = [1, 2, 6, 12, 24, 48, 72]

# Export formats
EXPORT_FORMATS = ["JSON", "CSV"]

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    'cpu_warning': float(os.getenv('CPU_WARNING_THRESHOLD', '70.0')),
    'cpu_critical': float(os.getenv('CPU_CRITICAL_THRESHOLD', '90.0')),
    'memory_warning': float(os.getenv('MEMORY_WARNING_THRESHOLD', '75.0')),
    'memory_critical': float(os.getenv('MEMORY_CRITICAL_THRESHOLD', '90.0')),
    'response_time_warning': float(os.getenv('RESPONSE_TIME_WARNING_MS', '2000.0')),
    'response_time_critical': float(os.getenv('RESPONSE_TIME_CRITICAL_MS', '5000.0'))
}

logger.info("Configuration loaded successfully")
