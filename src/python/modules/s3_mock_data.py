"""
S3 Mock Data Generator for Platform Monitoring

This module provides realistic mock data for S3 bucket monitoring,
simulating various storage scenarios for demo and testing purposes.
"""

import random
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
try:
    from .config_loader import get_config
except ImportError:
    from config_loader import get_config

logger = logging.getLogger(__name__)


class S3MockData:
    """
    S3 Mock Data Generator for realistic storage metrics simulation.
    
    Generates realistic bucket usage patterns, file counts, and utilization
    percentages for demonstration and testing purposes.
    """
    
    def __init__(self, environment: Optional[str] = None):
        """
        Initialize S3 mock data generator.
        
        Args:
            environment: Environment name for configuration loading
        """
        try:
            config = get_config(environment)
            self.s3_config = config.get('s3', {})
            self.buckets_config = self.s3_config.get('buckets', [])
        except Exception as e:
            logger.warning(f"Could not load S3 config for mock data: {e}")
            self.s3_config = {}
            self.buckets_config = []
        
        # Mock data patterns for different bucket types
        self.bucket_patterns = {
            'spark-data': {
                'base_utilization': (45, 75),
                'volatility': 0.15,
                'object_count_range': (5000, 50000),
                'growth_trend': 0.02
            },
            'spark-logs': {
                'base_utilization': (60, 85),
                'volatility': 0.25,
                'object_count_range': (10000, 100000),
                'growth_trend': 0.05
            },
            'platform-backups': {
                'base_utilization': (30, 60),
                'volatility': 0.10,
                'object_count_range': (100, 2000),
                'growth_trend': 0.01
            },
            'data-lake': {
                'base_utilization': (70, 90),
                'volatility': 0.08,
                'object_count_range': (50000, 500000),
                'growth_trend': 0.03
            },
            'ml-models': {
                'base_utilization': (25, 55),
                'volatility': 0.12,
                'object_count_range': (500, 5000),
                'growth_trend': 0.015
            },
            'analytics': {
                'base_utilization': (55, 80),
                'volatility': 0.18,
                'object_count_range': (20000, 150000),
                'growth_trend': 0.025
            },
            'customer-data': {
                'base_utilization': (40, 70),
                'volatility': 0.10,
                'object_count_range': (30000, 200000),
                'growth_trend': 0.02
            },
            'shared-storage': {
                'base_utilization': (35, 65),
                'volatility': 0.20,
                'object_count_range': (8000, 60000),
                'growth_trend': 0.03
            }
        }
        
        # Initialize random seed for consistent demo data
        random.seed(42)
        
        # Store previous values for realistic volatility
        self._previous_metrics = {}
    
    def generate_bucket_metrics(self, bucket_config: Dict) -> Dict:
        """
        Generate realistic metrics for a single S3 bucket.
        
        Args:
            bucket_config: Bucket configuration dictionary
            
        Returns:
            Dict: Generated bucket metrics
        """
        bucket_name = bucket_config.get('name', 'unknown')
        display_name = bucket_config.get('display_name', bucket_name)
        quota_gb = bucket_config.get('quota_gb', 100)
        alert_threshold = bucket_config.get('alert_threshold', 90)
        
        # Determine bucket pattern based on name
        pattern_key = self._get_bucket_pattern(bucket_name)
        pattern = self.bucket_patterns.get(pattern_key, self.bucket_patterns['spark-data'])
        
        # Generate utilization percentage
        utilization_pct = self._generate_utilization(bucket_name, pattern, alert_threshold)
        
        # Calculate storage values
        total_size_gb = (utilization_pct / 100.0) * quota_gb
        total_size_bytes = int(total_size_gb * (1024 ** 3))
        
        # Generate object count
        object_count = self._generate_object_count(bucket_name, pattern, total_size_gb)
        
        # Determine status
        status = self._get_status(utilization_pct, alert_threshold)
        
        # Add some realistic error scenarios occasionally
        error = None
        if random.random() < 0.05:  # 5% chance of error
            error = self._generate_error_scenario()
            if error:
                status = 'error'
        
        return {
            'bucket_name': bucket_name,
            'display_name': display_name,
            'total_size_bytes': total_size_bytes,
            'total_size_gb': round(total_size_gb, 2),
            'object_count': object_count,
            'quota_gb': quota_gb,
            'utilization_pct': round(utilization_pct, 1),
            'alert_threshold': alert_threshold,
            'status': status,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'error': error,
            # Additional mock metadata
            'endpoint_url': bucket_config.get('endpoint_url', 'mock-s3-endpoint'),
            'mock_data': True
        }
    
    def generate_all_bucket_metrics(self) -> List[Dict]:
        """
        Generate metrics for all configured S3 buckets.
        
        Returns:
            List[Dict]: List of bucket metrics dictionaries
        """
        if not self.buckets_config:
            logger.warning("No S3 buckets configured - generating sample buckets")
            return self._generate_sample_buckets()
        
        metrics_list = []
        for bucket_config in self.buckets_config:
            try:
                metrics = self.generate_bucket_metrics(bucket_config)
                metrics_list.append(metrics)
            except Exception as e:
                logger.error(f"Error generating mock data for bucket {bucket_config.get('name', 'unknown')}: {e}")
        
        return metrics_list
    
    def generate_platform_summary(self) -> Dict:
        """
        Generate overall platform storage summary.
        
        Returns:
            Dict: Platform-wide storage metrics
        """
        bucket_metrics = self.generate_all_bucket_metrics()
        
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
                'mock_data': True
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
            'mock_data': True
        }
    
    def _get_bucket_pattern(self, bucket_name: str) -> str:
        """
        Determine the pattern key for a bucket based on its name.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            str: Pattern key for bucket characteristics
        """
        name_lower = bucket_name.lower()
        
        if 'spark-data' in name_lower:
            return 'spark-data'
        elif 'spark-logs' in name_lower or 'logs' in name_lower:
            return 'spark-logs'
        elif 'backup' in name_lower:
            return 'platform-backups'
        elif 'data-lake' in name_lower or 'datalake' in name_lower:
            return 'data-lake'
        elif 'ml-model' in name_lower or 'model' in name_lower:
            return 'ml-models'
        elif 'analytics' in name_lower:
            return 'analytics'
        elif 'customer' in name_lower:
            return 'customer-data'
        elif 'shared' in name_lower:
            return 'shared-storage'
        else:
            return 'spark-data'  # default
    
    def _generate_utilization(self, bucket_name: str, pattern: Dict, alert_threshold: float) -> float:
        """
        Generate realistic utilization percentage with volatility and trends.
        
        Args:
            bucket_name: Name of the bucket
            pattern: Pattern configuration for the bucket type
            alert_threshold: Alert threshold percentage
            
        Returns:
            float: Generated utilization percentage
        """
        base_range = pattern['base_utilization']
        volatility = pattern['volatility']
        growth_trend = pattern['growth_trend']
        
        # Get previous value for smooth transitions
        prev_value = self._previous_metrics.get(bucket_name, {}).get('utilization_pct')
        
        if prev_value is None:
            # First generation - use base range
            base_utilization = random.uniform(base_range[0], base_range[1])
        else:
            # Apply volatility and growth trend
            change = random.gauss(growth_trend, volatility)
            base_utilization = prev_value + change
        
        # Add some randomness but keep within reasonable bounds
        utilization = base_utilization + random.uniform(-5, 5)
        
        # Ensure it stays within 0-100% range
        utilization = max(0, min(100, utilization))
        
        # Occasionally generate values near or over threshold for demo
        if random.random() < 0.15:  # 15% chance
            if random.random() < 0.5:
                # Near threshold
                utilization = alert_threshold + random.uniform(-5, 2)
            else:
                # Over threshold
                utilization = alert_threshold + random.uniform(2, 10)
        
        # Store for next generation
        if bucket_name not in self._previous_metrics:
            self._previous_metrics[bucket_name] = {}
        self._previous_metrics[bucket_name]['utilization_pct'] = utilization
        
        return max(0, min(100, utilization))
    
    def _generate_object_count(self, bucket_name: str, pattern: Dict, size_gb: float) -> int:
        """
        Generate realistic object count based on bucket size and type.
        
        Args:
            bucket_name: Name of the bucket
            pattern: Pattern configuration for the bucket type
            size_gb: Total size in GB
            
        Returns:
            int: Generated object count
        """
        base_range = pattern['object_count_range']
        
        # Scale object count based on size (with some randomness)
        size_factor = max(0.1, size_gb / 100.0)  # Normalize to 100GB baseline
        
        base_count = random.uniform(base_range[0], base_range[1]) * size_factor
        
        # Add some randomness
        variation = random.uniform(0.8, 1.2)
        object_count = int(base_count * variation)
        
        return max(1, object_count)
    
    def _generate_error_scenario(self) -> Optional[str]:
        """
        Generate realistic error scenarios for demonstration.
        
        Returns:
            Optional[str]: Error message or None
        """
        error_scenarios = [
            "Connection timeout to S3 endpoint",
            "Access denied - check bucket credentials",
            "Bucket does not exist or is not accessible", 
            "Network error connecting to S3 service",
            "S3 service temporarily unavailable",
            "Quota exceeded - unable to retrieve full metrics",
            "SSL certificate verification failed",
            "Rate limit exceeded - try again later"
        ]
        
        # 50% chance of no error even when this function is called
        if random.random() < 0.5:
            return None
        
        return random.choice(error_scenarios)
    
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
    
    def _generate_sample_buckets(self) -> List[Dict]:
        """
        Generate sample bucket metrics when no configuration is available.
        
        Returns:
            List[Dict]: Sample bucket metrics
        """
        sample_buckets = [
            {
                'name': 'spark-data-sample',
                'display_name': 'Spark Data (Sample)',
                'quota_gb': 500,
                'alert_threshold': 85
            },
            {
                'name': 'spark-logs-sample',
                'display_name': 'Spark Logs (Sample)',
                'quota_gb': 200,
                'alert_threshold': 80
            },
            {
                'name': 'platform-backups-sample',
                'display_name': 'Platform Backups (Sample)',
                'quota_gb': 1000,
                'alert_threshold': 90
            },
            {
                'name': 'analytics-sample',
                'display_name': 'Analytics Data (Sample)',
                'quota_gb': 750,
                'alert_threshold': 85
            }
        ]
        
        return [self.generate_bucket_metrics(bucket) for bucket in sample_buckets]
    
    def generate_folder_structure(self, bucket_name: str, bucket_metrics: Dict) -> List[Dict]:
        """
        Generate realistic folder structure for a bucket with 3 levels of depth.
        
        Args:
            bucket_name: Name of the bucket
            bucket_metrics: Bucket metrics containing total objects and size
            
        Returns:
            List of folder dictionaries with hierarchical structure
        """
        try:
            # Define folder patterns based on bucket type
            folder_patterns = {
                'spark-data': {
                    'root_folders': ['processed', 'raw', 'staging', 'archive'],
                    'subfolders': {
                        'processed': ['daily', 'monthly', 'yearly', 'reports'],
                        'raw': ['ingestion', 'streams', 'batch', 'external'],
                        'staging': ['temp', 'validation', 'cleanup', 'transform'],
                        'archive': ['2023', '2024', '2025', 'legacy']
                    },
                    'sub_subfolders': {
                        'daily': ['current', 'last_week', 'last_month'],
                        'monthly': ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'],
                        'yearly': ['metrics', 'summaries', 'exports'],
                        'reports': ['executive', 'operational', 'technical'],
                        'ingestion': ['api', 'files', 'database', 'streaming'],
                        'streams': ['kafka', 'kinesis', 'pubsub'],
                        'batch': ['hourly', 'daily', 'weekly'],
                        'external': ['partners', 'vendors', 'public'],
                        'temp': ['processing', 'failed', 'retry'],
                        'validation': ['passed', 'failed', 'pending'],
                        'cleanup': ['deleted', 'quarantine', 'restored'],
                        'transform': ['etl', 'mapping', 'rules'],
                        '2023': ['q1', 'q2', 'q3', 'q4'],
                        '2024': ['q1', 'q2', 'q3', 'q4'],
                        '2025': ['q1', 'q2', 'q3', 'q4'],
                        'legacy': ['pre2020', '2020', '2021', '2022']
                    }
                },
                'spark-logs': {
                    'root_folders': ['application', 'driver', 'executor', 'system'],
                    'subfolders': {
                        'application': ['job-logs', 'stage-logs', 'task-logs', 'error-logs'],
                        'driver': ['stdout', 'stderr', 'gc-logs', 'metrics'],
                        'executor': ['container-logs', 'shuffle-logs', 'block-manager', 'storage'],
                        'system': ['cluster-logs', 'resource-manager', 'node-manager', 'scheduler']
                    },
                    'sub_subfolders': {
                        'job-logs': ['completed', 'running', 'failed', 'cancelled'],
                        'stage-logs': ['map', 'reduce', 'join', 'aggregate'],
                        'task-logs': ['successful', 'retries', 'failures'],
                        'error-logs': ['exceptions', 'warnings', 'timeouts'],
                        'stdout': ['current', 'rotated', 'archived'],
                        'stderr': ['errors', 'warnings', 'debug'],
                        'gc-logs': ['g1gc', 'cms', 'parallel'],
                        'metrics': ['cpu', 'memory', 'disk', 'network'],
                        'container-logs': ['yarn', 'docker', 'k8s'],
                        'shuffle-logs': ['spill', 'fetch', 'write'],
                        'block-manager': ['storage', 'replication', 'eviction'],
                        'storage': ['disk', 'memory', 'off-heap'],
                        'cluster-logs': ['master', 'worker', 'history'],
                        'resource-manager': ['apps', 'queues', 'nodes'],
                        'node-manager': ['containers', 'local-dirs', 'log-dirs'],
                        'scheduler': ['fair', 'fifo', 'capacity']
                    }
                },
                'shared-storage': {
                    'root_folders': ['documents', 'media', 'backups', 'temp'],
                    'subfolders': {
                        'documents': ['contracts', 'reports', 'presentations', 'templates'],
                        'media': ['images', 'videos', 'audio', 'graphics'],
                        'backups': ['database', 'files', 'configs', 'logs'],
                        'temp': ['uploads', 'processing', 'cache', 'scratch']
                    },
                    'sub_subfolders': {
                        'contracts': ['active', 'expired', 'draft', 'signed'],
                        'reports': ['monthly', 'quarterly', 'annual', 'ad-hoc'],
                        'presentations': ['sales', 'technical', 'executive', 'training'],
                        'templates': ['documents', 'emails', 'forms', 'layouts'],
                        'images': ['logos', 'photos', 'icons', 'banners'],
                        'videos': ['tutorials', 'demos', 'recordings', 'promo'],
                        'audio': ['podcasts', 'calls', 'music', 'effects'],
                        'graphics': ['designs', 'mockups', 'assets', 'vectors'],
                        'database': ['daily', 'weekly', 'monthly', 'full'],
                        'files': ['incremental', 'full', 'differential'],
                        'configs': ['app', 'system', 'network', 'security'],
                        'logs': ['access', 'error', 'audit', 'system'],
                        'uploads': ['pending', 'processing', 'completed', 'failed'],
                        'processing': ['queue', 'active', 'completed', 'error'],
                        'cache': ['web', 'api', 'database', 'files'],
                        'scratch': ['temp1', 'temp2', 'temp3', 'cleanup']
                    }
                }
            }
            
            # Determine bucket type for folder patterns
            bucket_type = 'shared-storage'  # default
            for pattern_type in folder_patterns.keys():
                if pattern_type in bucket_name.lower():
                    bucket_type = pattern_type
                    break
            
            pattern = folder_patterns[bucket_type]
            total_objects = bucket_metrics.get('object_count', 10000)
            total_size_gb = bucket_metrics.get('total_size_gb', 50.0)
            
            # Generate folder structure
            folders = []
            remaining_objects = total_objects
            remaining_size = total_size_gb
            
            # Level 1: Root folders
            root_folders = pattern['root_folders']
            root_distribution = self._generate_distribution(len(root_folders), remaining_objects, remaining_size)
            
            for i, root_folder in enumerate(root_folders):
                root_objects = root_distribution['objects'][i]
                root_size = root_distribution['sizes'][i]
                
                # Level 2: Subfolders
                subfolders = pattern['subfolders'].get(root_folder, ['misc'])
                sub_distribution = self._generate_distribution(len(subfolders), root_objects, root_size)
                
                root_folder_data = {
                    'name': root_folder,
                    'level': 1,
                    'path': f"/{root_folder}",
                    'object_count': root_objects,
                    'size_gb': round(root_size, 2),
                    'size_percentage': round((root_size / total_size_gb) * 100, 1),
                    'last_modified': self._generate_recent_timestamp(),
                    'subfolders': []
                }
                
                for j, subfolder in enumerate(subfolders):
                    sub_objects = sub_distribution['objects'][j]
                    sub_size = sub_distribution['sizes'][j]
                    
                    # Level 3: Sub-subfolders
                    sub_subfolders = pattern['sub_subfolders'].get(subfolder, ['data'])
                    subsub_distribution = self._generate_distribution(len(sub_subfolders), sub_objects, sub_size)
                    
                    subfolder_data = {
                        'name': subfolder,
                        'level': 2,
                        'path': f"/{root_folder}/{subfolder}",
                        'object_count': sub_objects,
                        'size_gb': round(sub_size, 2),
                        'size_percentage': round((sub_size / total_size_gb) * 100, 1),
                        'last_modified': self._generate_recent_timestamp(),
                        'subfolders': []
                    }
                    
                    for k, sub_subfolder in enumerate(sub_subfolders):
                        subsub_objects = subsub_distribution['objects'][k]
                        subsub_size = subsub_distribution['sizes'][k]
                        
                        sub_subfolder_data = {
                            'name': sub_subfolder,
                            'level': 3,
                            'path': f"/{root_folder}/{subfolder}/{sub_subfolder}",
                            'object_count': subsub_objects,
                            'size_gb': round(subsub_size, 2),
                            'size_percentage': round((subsub_size / total_size_gb) * 100, 1),
                            'last_modified': self._generate_recent_timestamp(),
                            'avg_file_size_mb': round((subsub_size * 1024) / max(subsub_objects, 1), 2)
                        }
                        
                        subfolder_data['subfolders'].append(sub_subfolder_data)
                    
                    root_folder_data['subfolders'].append(subfolder_data)
                
                folders.append(root_folder_data)
            
            return folders
            
        except Exception as e:
            logger.error(f"Error generating folder structure: {e}")
            # Return simple fallback structure
            return [{
                'name': 'data',
                'level': 1,
                'path': '/data',
                'object_count': bucket_metrics.get('object_count', 1000),
                'size_gb': bucket_metrics.get('total_size_gb', 10.0),
                'size_percentage': 100.0,
                'last_modified': datetime.now(timezone.utc).isoformat(),
                'subfolders': []
            }]
    
    def _generate_distribution(self, num_items: int, total_objects: int, total_size: float) -> Dict:
        """
        Generate realistic distribution of objects and sizes across folders.
        
        Args:
            num_items: Number of items to distribute to
            total_objects: Total number of objects to distribute
            total_size: Total size to distribute
            
        Returns:
            Dict containing object and size distributions
        """
        if num_items == 0:
            return {'objects': [], 'sizes': []}
        
        # Generate random weights with some folders being larger than others
        weights = [random.uniform(0.1, 1.0) for _ in range(num_items)]
        total_weight = sum(weights)
        
        # Normalize weights and distribute
        objects_dist = []
        sizes_dist = []
        
        for i, weight in enumerate(weights):
            proportion = weight / total_weight
            
            # Add some randomness but ensure non-zero values
            obj_count = max(1, int(total_objects * proportion * random.uniform(0.7, 1.3)))
            size_val = max(0.01, total_size * proportion * random.uniform(0.7, 1.3))
            
            objects_dist.append(obj_count)
            sizes_dist.append(size_val)
        
        # Ensure totals match (adjust last item)
        if len(objects_dist) > 0:
            objects_diff = total_objects - sum(objects_dist)
            objects_dist[-1] = max(1, objects_dist[-1] + objects_diff)
            
            sizes_diff = total_size - sum(sizes_dist)
            sizes_dist[-1] = max(0.01, sizes_dist[-1] + sizes_diff)
        
        return {'objects': objects_dist, 'sizes': sizes_dist}
    
    def _generate_recent_timestamp(self) -> str:
        """Generate a recent timestamp for folder modification."""
        base_time = datetime.now(timezone.utc)
        random_offset = timedelta(
            hours=random.randint(1, 72),
            minutes=random.randint(0, 59)
        )
        return (base_time - random_offset).isoformat()

# Convenience function for easy access
def generate_mock_s3_data(environment: Optional[str] = None) -> Tuple[List[Dict], Dict]:
    """
    Generate complete S3 mock data including bucket metrics and platform summary.
    
    Args:
        environment: Environment name for configuration
        
    Returns:
        Tuple[List[Dict], Dict]: (bucket_metrics_list, platform_summary)
    """
    mock_generator = S3MockData(environment)
    bucket_metrics = mock_generator.generate_all_bucket_metrics()
    platform_summary = mock_generator.generate_platform_summary()
    
    logger.info(f"Generated mock S3 data for {len(bucket_metrics)} buckets")
    return bucket_metrics, platform_summary
