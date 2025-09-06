"""
Configuration settings for Spark Pod Resource Monitor
"""
import os
from pathlib import Path

# Database settings
DB_PATH = os.getenv('DB_PATH', 'spark_pods_history.db')
HISTORY_RETENTION_DAYS = int(os.getenv('HISTORY_RETENTION_DAYS', '7'))

# Default values
DEFAULT_API_SERVER = "https://api.your-cluster.openshift.com:6443"
DEFAULT_NAMESPACE = "spark-applications"
DEFAULT_REFRESH_INTERVAL = 30

# UI settings
PAGE_TITLE = "Spark Pod Resource Monitor"
PAGE_ICON = "🔥"
LAYOUT = "wide"

# View modes
VIEW_MODES = ["Current Status", "Historical Analysis", "Pod Timeline", "Export Data"]

# Time range options
TIME_RANGES = [1, 2, 6, 12, 24, 48, 72]

# Export formats
EXPORT_FORMATS = ["JSON", "CSV"]
