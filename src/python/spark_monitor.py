"""
Spark Pod Resource Monitor - Main Entry Point
"""
import sys
import os

# Add the modules directory to the path
sys.path.append(os.path.dirname(__file__))

# Import and run the main application
from modules.main import main

if __name__ == "__main__":
    main()