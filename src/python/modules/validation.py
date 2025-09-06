"""
Input validation and sanitization utilities
"""
import re
import logging
from urllib.parse import urlparse
from typing import Optional, Dict, Any
from logging_config import ValidationError

logger = logging.getLogger(__name__)


def validate_namespace(namespace: str) -> str:
    """
    Validate and sanitize Kubernetes namespace
    
    Args:
        namespace: Kubernetes namespace string
        
    Returns:
        str: Sanitized namespace
        
    Raises:
        ValidationError: If namespace format is invalid
    """
    if not namespace:
        raise ValidationError("Namespace cannot be empty")
    
    if not isinstance(namespace, str):
        raise ValidationError("Namespace must be a string")

    # Strip whitespace first
    namespace = namespace.strip().lower()
    
    if not namespace:
        raise ValidationError("Namespace cannot be empty after trimming whitespace")

    # Kubernetes namespace naming rules
    if not re.match(r'^[a-z0-9-]+$', namespace):
        raise ValidationError(
            "Namespace must contain only lowercase letters, numbers, and hyphens"
        )
    
    if len(namespace) > 63:
        raise ValidationError("Namespace must be 63 characters or less")
    
    if namespace.startswith('-') or namespace.endswith('-'):
        raise ValidationError("Namespace cannot start or end with a hyphen")
    
    logger.debug(f"Validated namespace: {namespace}")
    return namespace


def validate_api_server_url(url: str) -> str:
    """
    Validate Kubernetes API server URL
    
    Args:
        url: API server URL string
        
    Returns:
        str: Validated URL
        
    Raises:
        ValidationError: If URL format is invalid
    """
    if not url:
        raise ValidationError("API server URL cannot be empty")
    
    if not isinstance(url, str):
        raise ValidationError("API server URL must be a string")
    
    try:
        parsed = urlparse(url)
        
        if parsed.scheme not in ('http', 'https'):
            raise ValidationError("API server URL must use HTTP or HTTPS protocol")
        
        if not parsed.netloc:
            raise ValidationError("API server URL must include hostname")
        
        # Validate hostname format
        hostname = parsed.hostname
        if hostname and not re.match(r'^[a-zA-Z0-9.-]+$', hostname):
            raise ValidationError("Invalid hostname format in API server URL")
        
        logger.debug(f"Validated API server URL: {url}")
        return url.strip()
        
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Invalid API server URL format: {str(e)}")


def validate_token(token: str) -> str:
    """
    Validate Kubernetes service account token
    
    Args:
        token: Service account token
        
    Returns:
        str: Validated token
        
    Raises:
        ValidationError: If token format is invalid
    """
    if not token:
        raise ValidationError("Token cannot be empty")
    
    if not isinstance(token, str):
        raise ValidationError("Token must be a string")
    
    token = token.strip()
    
    # Basic token format validation
    if len(token) < 10:
        raise ValidationError("Token appears to be too short")
    
    if len(token) > 4096:
        raise ValidationError("Token appears to be too long")
    
    # Check for common token patterns (basic validation)
    if not re.match(r'^[A-Za-z0-9._-]+$', token):
        logger.warning("Token contains unusual characters")
    
    logger.debug("Token validation passed")
    return token


def validate_retention_days(days: int) -> int:
    """
    Validate data retention days
    
    Args:
        days: Number of retention days
        
    Returns:
        int: Validated retention days
        
    Raises:
        ValidationError: If retention days is invalid
    """
    if not isinstance(days, int):
        try:
            days = int(days)
        except (ValueError, TypeError):
            raise ValidationError("Retention days must be an integer")
    
    if not 1 <= days <= 365:
        raise ValidationError("Retention days must be between 1 and 365")
    
    logger.debug(f"Validated retention days: {days}")
    return days


def validate_refresh_interval(interval: int) -> int:
    """
    Validate refresh interval
    
    Args:
        interval: Refresh interval in seconds
        
    Returns:
        int: Validated refresh interval
        
    Raises:
        ValidationError: If refresh interval is invalid
    """
    if not isinstance(interval, int):
        try:
            interval = int(interval)
        except (ValueError, TypeError):
            raise ValidationError("Refresh interval must be an integer")
    
    if not 10 <= interval <= 3600:
        raise ValidationError("Refresh interval must be between 10 and 3600 seconds")
    
    logger.debug(f"Validated refresh interval: {interval}")
    return interval


def sanitize_pod_name(pod_name: str) -> str:
    """
    Sanitize pod name for safe database storage
    
    Args:
        pod_name: Pod name string
        
    Returns:
        str: Sanitized pod name
        
    Raises:
        ValidationError: If pod name is invalid
    """
    if not pod_name:
        raise ValidationError("Pod name cannot be empty")
    
    if not isinstance(pod_name, str):
        raise ValidationError("Pod name must be a string")
    
    # Remove any SQL injection attempts
    dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
    for char in dangerous_chars:
        if char in pod_name:
            logger.warning(f"Potentially dangerous character sequence found in pod name: {char}")
            pod_name = pod_name.replace(char, '_')
    
    # Kubernetes pod name validation
    if not re.match(r'^[a-z0-9-]+$', pod_name.lower()):
        logger.warning(f"Pod name contains non-standard characters: {pod_name}")
    
    return pod_name.strip()


def validate_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate entire configuration dictionary
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Dict[str, Any]: Validated configuration
        
    Raises:
        ValidationError: If any configuration value is invalid
    """
    validated_config = {}
    
    try:
        if 'namespace' in config:
            validated_config['namespace'] = validate_namespace(config['namespace'])
        
        if 'api_server_url' in config:
            validated_config['api_server_url'] = validate_api_server_url(config['api_server_url'])
        
        if 'token' in config and config['token']:
            validated_config['token'] = validate_token(config['token'])
        
        if 'retention_days' in config:
            validated_config['retention_days'] = validate_retention_days(config['retention_days'])
        
        if 'refresh_interval' in config:
            validated_config['refresh_interval'] = validate_refresh_interval(config['refresh_interval'])
        
        logger.info("Configuration validation completed successfully")
        return {**config, **validated_config}
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        raise
