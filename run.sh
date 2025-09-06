#!/bin/bash
# Run script for Spark Pod Resource Monitor

# Activate virtual environment
source spark-monitor-env/bin/activate

# Run the Streamlit application
streamlit run src/python/spark_monitor.py
