#!/bin/bash
# Run script for Spark Pod Resource Monitor
set -euo pipefail

# Function to detect the best Python executable
detect_python() {
    local python_cmd=""
    
    # Check for python3 first (preferred)
    if command -v python3 &> /dev/null; then
        local version=$(python3 --version 2>&1 | cut -d' ' -f2 2>/dev/null || echo "0.0.0")
        local major=$(echo $version | cut -d'.' -f1)
        local minor=$(echo $version | cut -d'.' -f2)
        
        if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
            python_cmd="python3"
        fi
    fi
    
    # If python3 not suitable, check python command
    if [ -z "$python_cmd" ] && command -v python &> /dev/null; then
        local version=$(python --version 2>&1 | cut -d' ' -f2 2>/dev/null || echo "0.0.0")
        local major=$(echo $version | cut -d'.' -f1)
        local minor=$(echo $version | cut -d'.' -f2)
        
        if [ "$major" -ge 3 ] && [ "$minor" -ge 8 ]; then
            python_cmd="python"
        fi
    fi
    
    if [ -z "$python_cmd" ]; then
        echo "Error: Python 3.8+ not found. Please install Python 3.8 or higher" >&2
        exit 1
    fi
    
    echo "$python_cmd"
}

# Function to detect virtual environment paths (Unix/Windows support)
detect_venv_paths() {
    local venv_name="$1"
    local venv_activate=""
    local venv_streamlit=""
    
    # Check for Unix/Linux/macOS structure
    if [ -f "$venv_name/bin/activate" ]; then
        venv_activate="$venv_name/bin/activate"
        venv_streamlit="$venv_name/bin/streamlit"
    # Check for Windows Git Bash structure
    elif [ -f "$venv_name/Scripts/activate" ]; then
        venv_activate="$venv_name/Scripts/activate"
        venv_streamlit="$venv_name/Scripts/streamlit.exe"
        # Also check for streamlit without .exe extension
        if [ ! -f "$venv_streamlit" ] && [ -f "$venv_name/Scripts/streamlit" ]; then
            venv_streamlit="$venv_name/Scripts/streamlit"
        fi
    fi
    
    echo "$venv_activate|$venv_streamlit"
}

# Detect Python executable
PYTHON_CMD=$(detect_python)

# Detect virtual environment paths
VENV_NAME="spark-monitor-env"
VENV_PATHS=$(detect_venv_paths "$VENV_NAME")
VENV_ACTIVATE=$(echo "$VENV_PATHS" | cut -d'|' -f1)
VENV_STREAMLIT=$(echo "$VENV_PATHS" | cut -d'|' -f2)

# Activate virtual environment if available
if [ -d "$VENV_NAME" ] && [ -n "$VENV_ACTIVATE" ] && [ -f "$VENV_ACTIVATE" ]; then
  # shellcheck source=/dev/null
  source "$VENV_ACTIVATE" || echo "Warning: Failed to activate venv, attempting system Python"
fi

PORT="${PORT:-8502}"
ADDRESS="${ADDRESS:-localhost}"

# Prefer venv streamlit if present and executable
if [ -n "$VENV_STREAMLIT" ] && [ -x "$VENV_STREAMLIT" ]; then
  exec "$VENV_STREAMLIT" run src/python/spark_monitor.py --server.port "$PORT" --server.address "$ADDRESS"
else
  # Fallback to detected python -m streamlit
  exec $PYTHON_CMD -m streamlit run src/python/spark_monitor.py --server.port "$PORT" --server.address "$ADDRESS"
fi
