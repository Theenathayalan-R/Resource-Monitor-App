"""
Environment-based configuration loader for Spark Pod Resource Monitor
Supports YAML configuration files with environment-specific settings
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from logging_config import ConfigurationError, setup_logging
except ImportError:
    # Fallback if logging_config not available
    class ConfigurationError(Exception):
        pass
    
    def setup_logging(level, file_path):
        logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    raise ImportError("PyYAML is required for configuration. Install with: pip install PyYAML")


class ConfigLoader:
    """Loads configuration from environment-specific YAML files"""
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.environment: str = ""
        self.logger = logging.getLogger(__name__)
        
    def load_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration for the specified environment
        
        Args:
            environment: Environment name (dev, staging, prod). 
                        If None, uses ENVIRONMENT env var or defaults to 'development'
        
        Returns:
            Dictionary containing the loaded configuration
            
        Raises:
            ConfigurationError: If configuration cannot be loaded or is invalid
        """
        # Determine environment
        if environment is None:
            environment = os.getenv('ENVIRONMENT', 'development').lower()
        
        self.environment = environment
        self.logger.info(f"Loading configuration for environment: {environment}")
        
        # Try to load configuration file
        config_data = self._load_config_file()
        
        # Extract environment-specific configuration
        if 'environments' not in config_data:
            raise ConfigurationError("Configuration file must contain 'environments' section")
            
        if environment not in config_data['environments']:
            available_envs = list(config_data['environments'].keys())
            raise ConfigurationError(
                f"Environment '{environment}' not found in configuration. "
                f"Available environments: {available_envs}"
            )
        
        # Get environment configuration
        env_config = config_data['environments'][environment]
        
        # Merge with global configuration
        if 'global' in config_data:
            env_config = self._merge_configs(config_data['global'], env_config)
        
        # Apply environment variable overrides
        env_config = self._apply_env_overrides(env_config)
        
        # Validate configuration
        self._validate_config(env_config)
        
        self.config = env_config
        self.logger.info("Configuration loaded successfully")
        return env_config
    
    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        # Start from the project root directory
        project_root = Path(__file__).parent.parent.parent.parent
        config_dir = project_root / 'config'
        
        # Look for YAML configuration files
        config_files = [
            config_dir / 'environments.yaml',
            config_dir / 'environments.yml'
        ]
        
        # Also check for custom config file via environment variable
        custom_config = os.getenv('CONFIG_FILE')
        if custom_config:
            config_files.insert(0, Path(custom_config))
        
        for config_file in config_files:
            if config_file.exists():
                self.logger.info(f"Loading configuration from: {config_file}")
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    self.logger.error(f"Error loading config file {config_file}: {e}")
                    continue
        
        raise ConfigurationError(
            f"No valid YAML configuration file found. Searched: {[str(f) for f in config_files]}\n"
            f"Please create a configuration file or install PyYAML: pip install PyYAML"
        )
    
    def _merge_configs(self, global_config: Dict[str, Any], env_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge global configuration with environment-specific configuration"""
        merged = global_config.copy()
        
        # Deep merge environment config over global config
        for key, value in env_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides for sensitive data like passwords"""
        
        # Database password override
        if 'database' in config and 'oracle' in config['database']:
            oracle_password = os.getenv('ORACLE_PASSWORD')
            if oracle_password:
                config['database']['oracle']['password'] = oracle_password
                self.logger.info("Oracle password loaded from environment variable")
        
        # Kubernetes token override
        if 'kubernetes' in config:
            k8s_token = os.getenv('KUBERNETES_TOKEN')
            if k8s_token:
                config['kubernetes']['token'] = k8s_token
                self.logger.info("Kubernetes token loaded from environment variable")
        
        return config
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate the loaded configuration"""
        required_sections = ['kubernetes', 'database', 'application']
        
        for section in required_sections:
            if section not in config:
                raise ConfigurationError(f"Required configuration section '{section}' not found")
        
        # Validate Kubernetes configuration
        k8s_config = config['kubernetes']
        required_k8s = ['api_server', 'namespace']
        for key in required_k8s:
            if not k8s_config.get(key):
                raise ConfigurationError(f"Required Kubernetes setting '{key}' not configured")
        
        # Validate database configuration
        db_config = config['database']
        if 'type' not in db_config:
            raise ConfigurationError("Database type not specified")
        
        db_type = db_config['type'].lower()
        if db_type not in ['sqlite', 'oracle']:
            raise ConfigurationError(f"Unsupported database type: {db_type}")
        
        if db_type == 'oracle':
            required_oracle = ['host', 'port', 'service_name', 'username']
            oracle_config = db_config.get('oracle', {})
            for key in required_oracle:
                if not oracle_config.get(key):
                    raise ConfigurationError(f"Required Oracle setting '{key}' not configured")
        
        # Validate data retention
        if 'data_retention' in config:
            retention_days = config['data_retention'].get('history_days', 7)
            if not isinstance(retention_days, int) or not (1 <= retention_days <= 365):
                raise ConfigurationError(f"history_days must be between 1 and 365, got {retention_days}")
        
        # Validate refresh interval
        if 'application' in config and 'refresh_interval' in config['application']:
            refresh_interval = config['application']['refresh_interval']
            if not isinstance(refresh_interval, int) or not (10 <= refresh_interval <= 3600):
                raise ConfigurationError(f"refresh_interval must be between 10 and 3600, got {refresh_interval}")


# Global configuration instance
_config_loader = None
_loaded_config = None


def get_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the loaded configuration for the specified environment
    
    Args:
        environment: Environment name (dev, staging, prod).
                    If None, uses ENVIRONMENT env var or defaults to 'development'
    
    Returns:
        Dictionary containing the configuration
    """
    global _config_loader, _loaded_config
    
    if _config_loader is None or _loaded_config is None:
        _config_loader = ConfigLoader()
        _loaded_config = _config_loader.load_config(environment)
    
    return _loaded_config


def reload_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """
    Force reload of configuration
    
    Args:
        environment: Environment name to load
        
    Returns:
        Dictionary containing the reloaded configuration
    """
    global _config_loader, _loaded_config
    
    _config_loader = ConfigLoader()
    _loaded_config = _config_loader.load_config(environment)
    
    return _loaded_config


def get_environment() -> str:
    """Get the current environment name"""
    if _config_loader:
        return _config_loader.environment
    return os.getenv('ENVIRONMENT', 'development').lower()
