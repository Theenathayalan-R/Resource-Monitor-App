"""
Kubernetes client operations for Spark Pod Resource Monitor
"""
import tempfile
import os
import yaml
import logging
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from config import TLS_VERIFY
from logging_config import KubernetesError, log_performance
from performance import monitor_performance, get_performance_monitor
from validation import validate_api_server_url, validate_token, validate_namespace

logger = logging.getLogger(__name__)


class KubernetesClient:
    def __init__(self, api_server_url: str, kubeconfig_token: str):
        self.api_server_url = validate_api_server_url(api_server_url)
        self.kubeconfig_token = validate_token(kubeconfig_token)
        self.v1 = None
        self.metrics_client = None
        self._connection_validated = False
        self._initialize_client()

    @log_performance
    def _initialize_client(self):
        """Initialize Kubernetes client with provided credentials and enhanced error handling"""
        kubeconfig_path = None
        try:
            logger.info(f"Initializing Kubernetes client for {self.api_server_url}")
            
            kubeconfig_content = {
                'apiVersion': 'v1',
                'kind': 'Config',
                'clusters': [{
                    'name': 'openshift-cluster',
                    'cluster': {
                        'server': self.api_server_url,
                        # Prefer TLS verification; allow disabling via config
                        'insecure-skip-tls-verify': not TLS_VERIFY
                    }
                }],
                'users': [{
                    'name': 'openshift-user',
                    'user': {
                        'token': self.kubeconfig_token
                    }
                }],
                'contexts': [{
                    'name': 'openshift-context',
                    'context': {
                        'cluster': 'openshift-cluster',
                        'user': 'openshift-user'
                    }
                }],
                'current-context': 'openshift-context'
            }

            # Create temporary kubeconfig file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
                yaml.dump(kubeconfig_content, f)
                kubeconfig_path = f.name

            # Load the kubeconfig
            config.load_kube_config(config_file=kubeconfig_path)
            self.v1 = client.CoreV1Api()
            
            # Test the connection
            self._test_connection()
            self._connection_validated = True
            logger.info("Kubernetes client initialized successfully")

        except ApiException as e:
            error_msg = f"Kubernetes API error during initialization: {e.status} - {e.reason}"
            if e.status == 401:
                error_msg = "Authentication failed. Please check your token."
            elif e.status == 403:
                error_msg = "Authorization failed. Please check your permissions."
            elif e.status == 404:
                error_msg = "API endpoint not found. Please check your API server URL."
            
            logger.error(error_msg, exc_info=True)
            raise KubernetesError(error_msg) from e
            
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {str(e)}", exc_info=True)
            raise KubernetesError(f"Failed to initialize Kubernetes client: {str(e)}") from e
            
        finally:
            # Always cleanup temporary kubeconfig file
            if kubeconfig_path and os.path.exists(kubeconfig_path):
                try:
                    os.unlink(kubeconfig_path)
                    logger.debug("Temporary kubeconfig file cleaned up")
                except Exception as e:
                    logger.warning(f"Failed to delete temporary kubeconfig file: {str(e)}")

    def _test_connection(self):
        """Test the connection to validate credentials and permissions"""
        try:
            # Try to list namespaces as a basic connectivity test
            self.v1.list_namespace(limit=1)
            logger.debug("Kubernetes connection test passed")
        except ApiException as e:
            if e.status == 403:
                # If we can't list namespaces, try a different endpoint
                logger.warning("Cannot list namespaces, trying alternative test")
                try:
                    self.v1.get_api_resources()
                except Exception:
                    raise KubernetesError("Insufficient permissions to access Kubernetes API")
            else:
                raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ApiException, ConnectionError))
    )
    @monitor_performance("kubernetes")
    def get_pods(self, namespace: str) -> List[Any]:
        """Get all pods in the specified namespace with retry logic"""
        try:
            namespace = validate_namespace(namespace)
            
            if not self._connection_validated:
                raise KubernetesError("Kubernetes client not properly initialized")
            
            # Record API call for performance monitoring
            get_performance_monitor().record_api_call()
            
            logger.debug(f"Fetching pods from namespace: {namespace}")
            pods_response = self.v1.list_namespaced_pod(
                namespace=namespace,
                timeout_seconds=30,
                limit=1000  # Reasonable limit for performance
            )
            
            pods = pods_response.items
            logger.info(f"Successfully retrieved {len(pods)} pods from namespace {namespace}")
            return pods
            
        except ApiException as e:
            error_msg = f"Kubernetes API error fetching pods from {namespace}: {e.status} - {e.reason}"
            if e.status == 404:
                error_msg = f"Namespace '{namespace}' not found or inaccessible"
            elif e.status == 403:
                error_msg = f"Permission denied accessing namespace '{namespace}'"
            
            logger.error(error_msg, exc_info=True)
            raise KubernetesError(error_msg) from e
            
        except Exception as e:
            logger.error(f"Unexpected error fetching pods from {namespace}: {str(e)}", exc_info=True)
            raise KubernetesError(f"Failed to fetch pods: {str(e)}") from e

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type((ApiException, ConnectionError))
    )
    @monitor_performance("kubernetes")
    def get_namespace_pod_metrics(self, namespace: str) -> Dict[str, Dict[str, float]]:
        """Batch fetch pod metrics for all pods in a namespace with enhanced error handling"""
        try:
            namespace = validate_namespace(namespace)
            
            # Record API call for performance monitoring
            get_performance_monitor().record_api_call()
            
            from kubernetes.client import CustomObjectsApi

            if not self.metrics_client:
                self.metrics_client = CustomObjectsApi(self.v1.api_client)

            logger.debug(f"Fetching metrics for namespace: {namespace}")
            
            metrics_list = self.metrics_client.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods",
                timeout_seconds=20
            )

            result = {}
            items = metrics_list.get('items', [])
            
            for item in items:
                try:
                    pod_name = item.get('metadata', {}).get('name')
                    if not pod_name:
                        continue
                        
                    cpu_usage = 0.0
                    memory_usage = 0.0
                    
                    for container in item.get('containers', []):
                        usage = container.get('usage', {})
                        
                        # Parse CPU usage
                        cpu_str = usage.get('cpu', '0')
                        if cpu_str:
                            cpu_usage += self._parse_cpu_usage(cpu_str)
                        
                        # Parse memory usage
                        mem_str = usage.get('memory', '0')
                        if mem_str:
                            memory_usage += self._parse_memory_usage(mem_str)
                    
                    result[pod_name] = {
                        'cpu_usage': round(cpu_usage, 3),
                        'memory_usage': round(memory_usage, 1)
                    }
                    
                except Exception as e:
                    logger.warning(f"Error parsing metrics for pod {pod_name}: {str(e)}")
                    continue
            
            logger.info(f"Successfully retrieved metrics for {len(result)} pods in {namespace}")
            return result
            
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Metrics API not available for namespace {namespace}")
                return {}
            else:
                logger.warning(f"Metrics API error: {e.status} - {e.reason}")
                return {}
                
        except Exception as e:
            logger.warning(f"Failed to fetch namespace metrics: {str(e)}")
            return {}

    def _parse_cpu_usage(self, cpu_str: str) -> float:
        """Parse CPU usage string to cores (float)"""
        try:
            if cpu_str.endswith('n'):
                return float(cpu_str[:-1]) / 1_000_000_000
            elif cpu_str.endswith('u'):
                return float(cpu_str[:-1]) / 1_000_000
            elif cpu_str.endswith('m'):
                return float(cpu_str[:-1]) / 1_000
            else:
                return float(cpu_str)
        except (ValueError, TypeError) as e:
            logger.debug(f"Error parsing CPU value '{cpu_str}': {str(e)}")
            return 0.0

    def _parse_memory_usage(self, mem_str: str) -> float:
        """Parse memory usage string to MiB (float)"""
        try:
            if mem_str.endswith('Ki'):
                return float(mem_str[:-2]) / 1024
            elif mem_str.endswith('Mi'):
                return float(mem_str[:-2])
            elif mem_str.endswith('Gi'):
                return float(mem_str[:-2]) * 1024
            elif mem_str.endswith('Ti'):
                return float(mem_str[:-2]) * 1024 * 1024
            else:
                # Assume bytes, convert to MiB
                return float(mem_str) / (1024 * 1024)
        except (ValueError, TypeError) as e:
            logger.debug(f"Error parsing memory value '{mem_str}': {str(e)}")
            return 0.0
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5)
    )
    @monitor_performance("kubernetes")
    def get_pod_metrics(self, namespace: str, pod_name: str) -> Dict[str, float]:
        """Get pod metrics (CPU, Memory usage) using Kubernetes Metrics API with fallback"""
        try:
            namespace = validate_namespace(namespace)
            pod_name = pod_name.strip() if pod_name else ""
            
            if not pod_name:
                logger.warning("Empty pod name provided for metrics")
                return {'cpu_usage': 0.0, 'memory_usage': 0.0}
            
            # Try batch metrics first for better performance
            try:
                metrics_map = self.get_namespace_pod_metrics(namespace)
                if pod_name in metrics_map:
                    return metrics_map[pod_name]
            except Exception as e:
                logger.debug(f"Batch metrics failed, falling back to single pod: {str(e)}")
            
            # Fallback to single pod request
            from kubernetes.client import CustomObjectsApi

            if not self.metrics_client:
                self.metrics_client = CustomObjectsApi(self.v1.api_client)

            # Record API call for performance monitoring
            get_performance_monitor().record_api_call()

            metrics = self.metrics_client.get_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods",
                name=pod_name,
                timeout_seconds=10
            )

            cpu_usage = 0.0
            memory_usage = 0.0

            containers = metrics.get('containers', []) if isinstance(metrics, dict) else []
            for container in containers:
                if not isinstance(container, dict):
                    continue
                    
                usage = container.get('usage', {})
                if not isinstance(usage, dict):
                    continue
                
                # Parse CPU usage
                cpu_str = usage.get('cpu', '0')
                if cpu_str:
                    cpu_usage += self._parse_cpu_usage(str(cpu_str))
                
                # Parse memory usage
                mem_str = usage.get('memory', '0')
                if mem_str:
                    memory_usage += self._parse_memory_usage(str(mem_str))

            result = {
                'cpu_usage': round(cpu_usage, 3),
                'memory_usage': round(memory_usage, 1)
            }
            
            logger.debug(f"Retrieved metrics for pod {pod_name}: {result}")
            return result

        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Pod {pod_name} not found in metrics API")
            else:
                logger.warning(f"Metrics API error for pod {pod_name}: {e.status} - {e.reason}")
            return {'cpu_usage': 0.0, 'memory_usage': 0.0}
            
        except Exception as e:
            logger.warning(f"Failed to fetch metrics for pod {pod_name}: {str(e)}")
            return {'cpu_usage': 0.0, 'memory_usage': 0.0}

    @monitor_performance("kubernetes") 
    def test_connection(self) -> bool:
        """Test the connection to the Kubernetes cluster"""
        try:
            if not self.v1:
                return False
                
            # Try a simple API call
            self.v1.list_namespace(limit=1, timeout_seconds=5)
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    def get_cluster_info(self) -> Dict[str, Any]:
        """Get basic cluster information for diagnostics"""
        try:
            if not self.v1:
                return {'status': 'not_connected', 'error': 'Client not initialized'}
            
            # Get server version
            version_api = client.VersionApi(self.v1.api_client)
            version_info = version_api.get_code()
            
            # Get node count (if permitted)
            try:
                nodes = self.v1.list_node(limit=1)
                node_count = len(nodes.items) if hasattr(nodes, 'items') else 'unknown'
            except Exception:
                node_count = 'permission_denied'
            
            return {
                'status': 'connected',
                'server_version': f"{version_info.major}.{version_info.minor}",
                'git_version': version_info.git_version,
                'platform': version_info.platform,
                'node_count': node_count,
                'api_server': self.api_server_url,
                'tls_verify': TLS_VERIFY
            }
            
        except Exception as e:
            logger.error(f"Failed to get cluster info: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'api_server': self.api_server_url
            }
