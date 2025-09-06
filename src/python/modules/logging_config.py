"""
Logging configuration for Spark Pod Resource Monitor
"""
import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(log_level='INFO', log_file=None):
    """
    Set up logging configuration for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path. If None, logs to console only.
    """
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(exist_ok=True)
    
    # Configure logging format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific loggers for third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('kubernetes').setLevel(logging.INFO)
    logging.getLogger('plotly').setLevel(logging.WARNING)
    
    return root_logger


def log_performance(func):
    """Decorator to monitor function performance"""
    import time
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = time.time()
        
        try:
            logger.debug(f"Starting {func.__name__} with args: {args[:2] if args else 'None'}")
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            if duration > 1.0:  # Log slow operations
                logger.warning(f"{func.__name__} completed in {duration:.2f}s (slow)")
            else:
                logger.debug(f"{func.__name__} completed in {duration:.3f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.2f}s: {str(e)}", exc_info=True)
            raise
    
    return wrapper


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class KubernetesError(Exception):
    """Custom exception for Kubernetes operations"""
    pass


class ValidationError(Exception):
    """Custom exception for input validation"""
    pass


class ConfigurationError(Exception):
    """Custom exception for configuration issues"""
    pass
