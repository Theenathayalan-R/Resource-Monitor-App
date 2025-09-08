"""
S3 Storage Adapter for Platform Monitoring

This module provides functionality to monitor S3 bucket utilization,
file counts, and storage metrics for comprehensive platform monitoring.
"""

import os
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception

from typing import Dict, List, Optional, Tuple, Union
import logging
from datetime import datetime, timezone
try:
    from .config_loader import get_config
except ImportError:
    from config_loader import get_config


logger = logging.getLogger(__name__)


class S3Adapter:
    """
    S3 Storage Adapter for monitoring bucket utilization and file metrics.
    
    Supports both AWS S3 and S3-compatible storage endpoints with
    configurable quotas and alert thresholds.
    """
    
    def __init__(self, environment: Optional[str] = None, mock_mode: bool = False):
        """
        Initialize S3 adapter with configuration.
        
        Args:
            environment: Environment name for configuration loading
            mock_mode: Whether to use mock data instead of real S3 connections
        """
        if not BOTO3_AVAILABLE and not mock_mode:
            logger.error("boto3 not available. Install with: pip install boto3")
            self.client = None
            self.s3_config = {}
            self.mock_mode = False
            return
            
        # Load configuration
        config = get_config(environment)
        self.s3_config = config.get('s3', {})
        self.mock_mode = mock_mode
        
        if mock_mode:
            logger.info("S3 adapter initialized in mock mode")
            self.client = None
            # Initialize mock data generator
            try:
                from .s3_mock_data import S3MockData
            except ImportError:
                from s3_mock_data import S3MockData
            self.mock_generator = S3MockData(environment)
        elif not self.s3_config.get('enabled', False):
            logger.warning("S3 monitoring is disabled in configuration")
            self.client = None
        else:
            # Initialize S3 clients (one per unique endpoint/credentials combination)
            self.clients = self._initialize_s3_clients()
        
        # Cache for bucket metrics
        self._metrics_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    def _initialize_s3_clients(self) -> Dict[str, object]:
        """
        Initialize S3 clients for different endpoint/credential combinations.
        
        Returns:
            Dict[str, object]: Dictionary mapping bucket names to S3 clients
        """
        if not BOTO3_AVAILABLE:
            return {}
            
        clients = {}
        buckets = self.s3_config.get('buckets', [])
        
        # Get default credentials
        default_access_key = (
            self.s3_config.get('default_access_key_id') or 
            os.getenv('AWS_ACCESS_KEY_ID')
        )
        default_secret_key = (
            self.s3_config.get('default_secret_access_key') or 
            os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        default_endpoint = self.s3_config.get('default_endpoint_url', '')
        
        for bucket_config in buckets:
            bucket_name = bucket_config.get('name')
            if not bucket_name:
                continue
                
            try:
                # Get bucket-specific credentials or use defaults
                access_key = (
                    bucket_config.get('access_key_id') or 
                    self._get_env_var_for_bucket(bucket_name, 'ACCESS_KEY_ID') or
                    default_access_key
                )
                secret_key = (
                    bucket_config.get('secret_access_key') or 
                    self._get_env_var_for_bucket(bucket_name, 'SECRET_KEY') or
                    default_secret_key
                )
                endpoint_url = bucket_config.get('endpoint_url') or default_endpoint
                
                if not access_key or not secret_key:
                    logger.warning(f"No credentials found for bucket {bucket_name}")
                    continue
                
                # Create client configuration
                client_config = {
                    'aws_access_key_id': access_key,
                    'aws_secret_access_key': secret_key
                }
                
                # Add region only if specified
                region = bucket_config.get('region') or self.s3_config.get('region')
                if region:
                    client_config['region_name'] = region
                
                # Add custom endpoint if specified
                if endpoint_url:
                    client_config['endpoint_url'] = endpoint_url
                    logger.debug(f"Using endpoint {endpoint_url} for bucket {bucket_name}")
                
                # Create client
                client = boto3.client('s3', **client_config)
                
                # Test connection (optional - can be disabled for faster startup)
                # client.list_buckets()
                
                clients[bucket_name] = client
                logger.debug(f"Initialized S3 client for bucket {bucket_name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize S3 client for bucket {bucket_name}: {e}")
                continue
        
        logger.info(f"Initialized {len(clients)} S3 clients for buckets")
        return clients
    
    def _get_env_var_for_bucket(self, bucket_name: str, suffix: str) -> Optional[str]:
        """
        Get environment variable for bucket-specific credentials.
        
        Args:
            bucket_name: Name of the bucket
            suffix: Suffix for the environment variable (e.g., 'ACCESS_KEY_ID')
            
        Returns:
            Optional[str]: Environment variable value or None
        """
        # Convert bucket name to env var format
        env_var_base = bucket_name.upper().replace('-', '_')
        env_var_name = f"{env_var_base}_{suffix}"
        
        return os.getenv(env_var_name)
    
    def _initialize_s3_client(self) -> Optional[object]:
        """
        Legacy method for backward compatibility.
        
        Returns:
            Optional[object]: S3 client instance or None
        """
        # This method is kept for backward compatibility but not used in multi-client mode
        return None
        """
        Initialize AWS S3 client with configuration.
        
        Returns:
            boto3.client: S3 client instance or None if initialization fails
        """
        if not BOTO3_AVAILABLE:
            return None
            
        try:
            # Get credentials from environment or configuration
            access_key = (
                self.s3_config.get('access_key_id') or 
                os.getenv('AWS_ACCESS_KEY_ID')
            )
            secret_key = (
                self.s3_config.get('secret_access_key') or 
                os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            
            if not access_key or not secret_key:
                logger.error("S3 credentials not found in environment or configuration")
                return None
            
            # Initialize client with configuration
            client_config = {
                'aws_access_key_id': access_key,
                'aws_secret_access_key': secret_key
            }
            
            # Add region only if specified (not needed for on-premises S3)
            region = self.s3_config.get('region')
            if region:
                client_config['region_name'] = region
            
            # Add custom endpoint if specified (for S3-compatible storage)
            endpoint_url = self.s3_config.get('endpoint_url')
            if endpoint_url:
                client_config['endpoint_url'] = endpoint_url
                logger.info(f"Using custom S3 endpoint: {endpoint_url}")
            
            client = boto3.client('s3', **client_config)
            
            # Test connection
            client.list_buckets()
            logger.info("S3 client initialized successfully")
            return client
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            return None
        except ClientError as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error initializing S3 client: {e}")
            return None
    
    def is_enabled(self) -> bool:
        """
        Check if S3 monitoring is enabled and functional.
        
        Returns:
            bool: True if S3 monitoring is enabled and functional
        """
        if self.mock_mode:
            return True
            
        return (
            self.s3_config.get('enabled', False) and 
            (hasattr(self, 'clients') and len(getattr(self, 'clients', {})) > 0)
        )
    
    def get_bucket_metrics(self, bucket_name: str) -> Dict:
        """
        Get comprehensive metrics for a specific S3 bucket.
        
        Args:
            bucket_name: Name of the S3 bucket
            
        Returns:
            Dict: Bucket metrics including size, object count, utilization percentage
        """
        if self.mock_mode:
            # Use mock data generator
            bucket_config = self._get_bucket_config(bucket_name)
            if bucket_config:
                return self.mock_generator.generate_bucket_metrics(bucket_config)
            else:
                return self._empty_metrics(bucket_name, "Bucket not configured for mock mode")
        
        if not self.is_enabled():
            return self._empty_metrics(bucket_name, "S3 monitoring disabled")
        
        try:
            # Get bucket configuration
            bucket_config = self._get_bucket_config(bucket_name)
            if not bucket_config:
                return self._empty_metrics(bucket_name, "Bucket not configured")
            
            # Get client for this bucket
            client = getattr(self, 'clients', {}).get(bucket_name)
            if not client:
                return self._empty_metrics(bucket_name, "No S3 client available for this bucket")
            
            # Calculate bucket usage
            total_size_bytes, object_count = self._calculate_bucket_usage_with_client(client, bucket_name)
            
            # Convert to GB
            total_size_gb = total_size_bytes / (1024 ** 3)
            quota_gb = bucket_config.get('quota_gb', 0)
            
            # Calculate utilization percentage
            utilization_pct = (total_size_gb / quota_gb * 100) if quota_gb > 0 else 0
            
            # Determine status based on alert threshold
            alert_threshold = bucket_config.get('alert_threshold', 90)
            status = self._get_status(utilization_pct, alert_threshold)
            
            metrics = {
                'bucket_name': bucket_name,
                'display_name': bucket_config.get('display_name', bucket_name),
                'total_size_bytes': total_size_bytes,
                'total_size_gb': round(total_size_gb, 2),
                'object_count': object_count,
                'quota_gb': quota_gb,
                'utilization_pct': round(utilization_pct, 1),
                'alert_threshold': alert_threshold,
                'status': status,
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'error': None,
                'endpoint_url': bucket_config.get('endpoint_url', ''),
                'mock_data': False
            }
            
            logger.debug(f"Bucket metrics for {bucket_name}: {utilization_pct:.1f}% used")
            return metrics
            
        except ClientError as e:
            error_msg = f"AWS error accessing bucket {bucket_name}: {e}"
            logger.error(error_msg)
            return self._empty_metrics(bucket_name, error_msg)
        except Exception as e:
            error_msg = f"Error getting metrics for bucket {bucket_name}: {e}"
            logger.error(error_msg)
            return self._empty_metrics(bucket_name, error_msg)
    
    def get_all_bucket_metrics(self, use_cache: bool = True) -> List[Dict]:
        """
        Get metrics for all configured S3 buckets.
        
        Args:
            use_cache: Whether to use cached results if available
            
        Returns:
            List[Dict]: List of bucket metrics dictionaries
        """
        if self.mock_mode:
            return self.mock_generator.generate_all_bucket_metrics()
        
        if not self.is_enabled():
            return []
        
        # Check cache
        if use_cache and self._is_cache_valid():
            logger.debug("Using cached bucket metrics")
            return self._metrics_cache.get('all_buckets', [])
        
        buckets = self.s3_config.get('buckets', [])
        if not buckets:
            logger.warning("No S3 buckets configured for monitoring")
            return []
        
        metrics_list = []
        for bucket_config in buckets:
            bucket_name = bucket_config.get('name')
            if bucket_name:
                metrics = self.get_bucket_metrics(bucket_name)
                metrics_list.append(metrics)
        
        # Update cache
        self._metrics_cache['all_buckets'] = metrics_list
        self._cache_timestamp = datetime.now()
        
        return metrics_list
    
    def get_platform_summary(self) -> Dict:
        """
        Get overall platform storage summary across all S3 buckets.
        
        Returns:
            Dict: Platform-wide storage metrics and status
        """
        if self.mock_mode:
            return self.mock_generator.generate_platform_summary()
        
        if not self.is_enabled():
            return {
                'total_buckets': 0,
                'total_size_gb': 0,
                'total_objects': 0,
                'total_quota_gb': 0,
                'average_utilization': 0,
                'buckets_over_threshold': 0,
                'status': 'disabled',
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'mock_data': False
            }
        
        bucket_metrics = self.get_all_bucket_metrics()
        
        if not bucket_metrics:
            return {
                'total_buckets': 0,
                'total_size_gb': 0,
                'total_objects': 0,
                'total_quota_gb': 0,
                'average_utilization': 0,
                'buckets_over_threshold': 0,
                'status': 'no_data',
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'mock_data': False
            }
        
        # Calculate totals
        total_size_gb = sum(m['total_size_gb'] for m in bucket_metrics)
        total_objects = sum(m['object_count'] for m in bucket_metrics)
        total_quota_gb = sum(m['quota_gb'] for m in bucket_metrics)
        
        # Calculate average utilization
        valid_metrics = [m for m in bucket_metrics if m['quota_gb'] > 0]
        average_utilization = (
            sum(m['utilization_pct'] for m in valid_metrics) / len(valid_metrics)
            if valid_metrics else 0
        )
        
        # Count buckets over threshold
        buckets_over_threshold = sum(
            1 for m in bucket_metrics 
            if m['utilization_pct'] >= m['alert_threshold']
        )
        
        # Determine overall status
        if buckets_over_threshold > 0:
            status = 'critical'
        elif average_utilization > 80:
            status = 'warning'
        else:
            status = 'healthy'
        
        return {
            'total_buckets': len(bucket_metrics),
            'total_size_gb': round(total_size_gb, 2),
            'total_objects': total_objects,
            'total_quota_gb': total_quota_gb,
            'average_utilization': round(average_utilization, 1),
            'buckets_over_threshold': buckets_over_threshold,
            'status': status,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'mock_data': False
        }
    
    def _calculate_bucket_usage_with_client(self, client: object, bucket_name: str) -> Tuple[int, int]:
        """
        Calculate total size and object count for a bucket using specific client.
        
        Args:
            client: S3 client instance for this bucket
            bucket_name: Name of the S3 bucket
            
        Returns:
            Tuple[int, int]: (total_size_bytes, object_count)
        """
        total_size = 0
        object_count = 0
        
        if not client:
            return 0, 0
        
        try:
            paginator = client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket_name)
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
                        object_count += 1
            
            return total_size, object_count
            
        except ClientError as e:
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchBucket':
                logger.warning(f"Bucket {bucket_name} does not exist")
            else:
                logger.error(f"Error calculating bucket usage for {bucket_name}: {e}")
            return 0, 0
        except Exception as e:
            logger.error(f"Unexpected error calculating bucket usage for {bucket_name}: {e}")
            return 0, 0
    
    def _calculate_bucket_usage(self, bucket_name: str) -> Tuple[int, int]:
        """
        Legacy method for backward compatibility.
        
        Args:
            bucket_name: Name of the S3 bucket
            
        Returns:
            Tuple[int, int]: (total_size_bytes, object_count)
        """
        # Get client for this bucket
        client = getattr(self, 'clients', {}).get(bucket_name)
        if client:
            return self._calculate_bucket_usage_with_client(client, bucket_name)
        else:
            logger.warning(f"No client available for bucket {bucket_name}")
            return 0, 0
        """
        Calculate total size and object count for a bucket.
        
        Args:
            bucket_name: Name of the S3 bucket
            
        Returns:
            Tuple[int, int]: (total_size_bytes, object_count)
        """
        total_size = 0
        object_count = 0
        
        if not self.client:
            return 0, 0
        
        try:
            paginator = self.client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket_name)
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
                        object_count += 1
            
            return total_size, object_count
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code') if hasattr(e, 'response') else 'Unknown'
            if error_code == 'NoSuchBucket':
                logger.warning(f"Bucket {bucket_name} does not exist")
            else:
                logger.error(f"Error calculating bucket usage for {bucket_name}: {e}")
            return 0, 0
        except Exception as e:
            logger.error(f"Unexpected error calculating bucket usage for {bucket_name}: {e}")
            return 0, 0
    
    def _get_bucket_config(self, bucket_name: str) -> Optional[Dict]:
        """
        Get configuration for a specific bucket.
        
        Args:
            bucket_name: Name of the S3 bucket
            
        Returns:
            Optional[Dict]: Bucket configuration or None if not found
        """
        buckets = self.s3_config.get('buckets', [])
        for bucket_config in buckets:
            if bucket_config.get('name') == bucket_name:
                return bucket_config
        return None
    
    def _get_status(self, utilization_pct: float, alert_threshold: float) -> str:
        """
        Determine status based on utilization and threshold.
        
        Args:
            utilization_pct: Current utilization percentage
            alert_threshold: Alert threshold percentage
            
        Returns:
            str: Status ('healthy', 'warning', 'critical')
        """
        if utilization_pct >= alert_threshold:
            return 'critical'
        elif utilization_pct >= alert_threshold * 0.8:  # 80% of threshold
            return 'warning'
        else:
            return 'healthy'
    
    def _empty_metrics(self, bucket_name: str, error_msg: Optional[str] = None) -> Dict:
        """
        Return empty metrics structure with error information.
        
        Args:
            bucket_name: Name of the bucket
            error_msg: Error message to include
            
        Returns:
            Dict: Empty metrics structure
        """
        bucket_config = self._get_bucket_config(bucket_name) or {}
        
        return {
            'bucket_name': bucket_name,
            'display_name': bucket_config.get('display_name', bucket_name),
            'total_size_bytes': 0,
            'total_size_gb': 0,
            'object_count': 0,
            'quota_gb': bucket_config.get('quota_gb', 0),
            'utilization_pct': 0,
            'alert_threshold': bucket_config.get('alert_threshold', 90),
            'status': 'error',
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'error': error_msg
        }
    
    def _is_cache_valid(self) -> bool:
        """
        Check if the metrics cache is still valid.
        
        Returns:
            bool: True if cache is valid and can be used
        """
        if not self._cache_timestamp:
            return False
        
        cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
        return cache_age < self._cache_ttl
    
    def clear_cache(self):
        """Clear the metrics cache to force fresh data retrieval."""
        self._metrics_cache = {}
        self._cache_timestamp = None
        logger.debug("S3 metrics cache cleared")
    
    def get_bucket_folder_structure(self, bucket_name: str) -> List[Dict]:
        """
        Get folder structure for a specific bucket with 3 levels of depth.
        
        Args:
            bucket_name: Name of the bucket to analyze
            
        Returns:
            List[Dict]: Hierarchical folder structure data
        """
        if not self.is_enabled():
            logger.warning("S3 adapter not enabled - cannot get folder structure")
            return []
        
        try:
            if self.mock_mode:
                # Use mock data generator
                if hasattr(self, 'mock_generator') and self.mock_generator:
                    # First get bucket metrics
                    bucket_metrics = None
                    all_metrics = self.get_all_bucket_metrics()
                    
                    for bucket in all_metrics:
                        if bucket['bucket_name'] == bucket_name:
                            bucket_metrics = bucket
                            break
                    
                    if bucket_metrics:
                        return self.mock_generator.generate_folder_structure(bucket_name, bucket_metrics)
                    else:
                        logger.warning(f"Bucket {bucket_name} not found in metrics")
                        return []
                else:
                    logger.error("Mock generator not available")
                    return []
            else:
                # Real S3 implementation would go here
                # For now, return empty list for real S3 mode
                logger.info("Real S3 folder structure analysis not yet implemented")
                return []
                
        except Exception as e:
            logger.error(f"Error getting folder structure for bucket {bucket_name}: {e}")
            return []
    
    def get_bucket_folder_structure(self, bucket_name: str) -> List[Dict]:
        """
        Get folder structure for a specific bucket with 3 levels of depth.
        
        Args:
            bucket_name: Name of the bucket to analyze
            
        Returns:
            List[Dict]: Hierarchical folder structure data
        """
        if not self.is_enabled():
            logger.warning("S3 adapter not enabled - cannot get folder structure")
            return []
        
        try:
            if self.mock_mode:
                # Use mock data generator
                if hasattr(self, 'mock_generator') and self.mock_generator:
                    # First get bucket metrics
                    bucket_metrics = None
                    all_metrics = self.get_all_bucket_metrics()
                    
                    for bucket in all_metrics:
                        if bucket['bucket_name'] == bucket_name:
                            bucket_metrics = bucket
                            break
                    
                    if bucket_metrics:
                        return self.mock_generator.generate_folder_structure(bucket_name, bucket_metrics)
                    else:
                        logger.warning(f"Bucket {bucket_name} not found in metrics")
                        return []
                else:
                    logger.error("Mock generator not available")
                    return []
            else:
                # Real S3 implementation would go here
                # For now, return empty list for real S3 mode
                logger.info("Real S3 folder structure analysis not yet implemented")
                return []
                
        except Exception as e:
            logger.error(f"Error getting folder structure for bucket {bucket_name}: {e}")
            return []
