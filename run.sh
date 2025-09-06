#!/bin/bash
# Run script for Spark Pod Resource Monitor
set -euo pipefail

# Activate virtual environment if available
if [ -d "spark-monitor-env" ] && [ -f "spark-monitor-env/bin/activate" ]; then
  # shellcheck source=/dev/null
  source spark-monitor-env/bin/activate || echo "Warning: Failed to activate venv, attempting system Python"
fi

# Prefer venv streamlit if present
if [ -x "spark-monitor-env/bin/streamlit" ]; then
  exec spark-monitor-env/bin/streamlit run src/python/spark_monitor.py
else
  # Fallback to python -m streamlit
  exec python -m streamlit run src/python/spark_monitor.py
fi
