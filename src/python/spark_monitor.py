"""
Spark Pod Resource Monitor - Main Entry Point
"""
import sys
import os

# Add the modules directory to the path
modules_path = os.path.join(os.path.dirname(__file__), 'modules')
sys.path.insert(0, modules_path)

# Import and run the main application
from main import main

if __name__ == "__main__":
    main()