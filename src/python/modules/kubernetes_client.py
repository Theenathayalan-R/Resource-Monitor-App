"""
Kubernetes client operations for Spark Pod Resource Monitor
"""
import tempfile
import os
import yaml
import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from .config import TLS_VERIFY

logger = logging.getLogger(__name__)


class KubernetesClient:
    def __init__(self, api_server_url, kubeconfig_token):
        self.api_server_url = api_server_url
        self.kubeconfig_token = kubeconfig_token
        self.v1 = None
        self.metrics_client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Kubernetes client with provided credentials"""
        kubeconfig_path = None
        try:
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

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
                yaml.dump(kubeconfig_content, f)
                kubeconfig_path = f.name

            config.load_kube_config(config_file=kubeconfig_path)
            self.v1 = client.CoreV1Api()

        except Exception as e:
            logger.exception("Failed to initialize Kubernetes client")
            raise Exception(f"Failed to initialize Kubernetes client: {str(e)}")
        finally:
            if kubeconfig_path and os.path.exists(kubeconfig_path):
                try:
                    os.unlink(kubeconfig_path)
                except Exception:
                    logger.warning("Failed to delete temporary kubeconfig file: %s", kubeconfig_path)

    def get_pods(self, namespace):
        """Get all pods in the specified namespace"""
        try:
            pods = self.v1.list_namespaced_pod(namespace=namespace)
            return pods.items
        except ApiException as e:
            logger.exception("Error fetching pods for namespace %s", namespace)
            raise Exception(f"Error fetching pods: {e}")

    def get_namespace_pod_metrics(self, namespace):
        """Batch fetch pod metrics for all pods in a namespace.
        Returns a dict of {pod_name: {cpu_usage, memory_usage}}.
        """
        try:
            from kubernetes.client import CustomObjectsApi

            if not self.metrics_client:
                self.metrics_client = CustomObjectsApi(self.v1.api_client)

            metrics_list = self.metrics_client.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods"
            )

            result = {}
            items = metrics_list.get('items', [])
            for item in items:
                pod_name = item.get('metadata', {}).get('name')
                cpu_usage = 0.0
                memory_usage = 0.0
                for container in item.get('containers', []):
                    usage = container.get('usage', {})
                    cpu_str = usage.get('cpu')
                    if cpu_str:
                        if cpu_str.endswith('n'):
                            cpu_usage += float(cpu_str[:-1]) / 1_000_000_000
                        elif cpu_str.endswith('m'):
                            cpu_usage += float(cpu_str[:-1]) / 1_000
                        else:
                            cpu_usage += float(cpu_str)
                    mem_str = usage.get('memory')
                    if mem_str:
                        if mem_str.endswith('Ki'):
                            memory_usage += float(mem_str[:-2]) / 1024
                        elif mem_str.endswith('Mi'):
                            memory_usage += float(mem_str[:-2])
                        elif mem_str.endswith('Gi'):
                            memory_usage += float(mem_str[:-2]) * 1024
                        else:
                            memory_usage += float(mem_str) / (1024 * 1024)
                if pod_name:
                    result[pod_name] = {'cpu_usage': cpu_usage, 'memory_usage': memory_usage}
            return result
        except Exception:
            logger.warning("Metrics API is unavailable or returned an error; defaulting to zeros")
            return {}

    def get_pod_metrics(self, namespace, pod_name):
        """Get pod metrics (CPU, Memory usage) using Kubernetes Metrics API"""
        # Prefer batch metrics where possible; fallback to per-pod request
        try:
            metrics_map = self.get_namespace_pod_metrics(namespace)
            if pod_name in metrics_map:
                return metrics_map[pod_name]
        except Exception:
            # Fall through to single pod fetch
            pass
        try:
            from kubernetes.client import CustomObjectsApi

            if not self.metrics_client:
                self.metrics_client = CustomObjectsApi(self.v1.api_client)

            metrics = self.metrics_client.get_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods",
                name=pod_name
            )

            cpu_usage = 0.0
            memory_usage = 0.0

            if 'containers' in metrics:
                for container in metrics['containers']:
                    usage = container.get('usage', {})
                    cpu_str = usage.get('cpu')
                    if cpu_str:
                        if cpu_str.endswith('n'):
                            cpu_usage += float(cpu_str[:-1]) / 1_000_000_000
                        elif cpu_str.endswith('m'):
                            cpu_usage += float(cpu_str[:-1]) / 1_000
                        else:
                            cpu_usage += float(cpu_str)
                    mem_str = usage.get('memory')
                    if mem_str:
                        if mem_str.endswith('Ki'):
                            memory_usage += float(mem_str[:-2]) / 1024
                        elif mem_str.endswith('Mi'):
                            memory_usage += float(mem_str[:-2])
                        elif mem_str.endswith('Gi'):
                            memory_usage += float(mem_str[:-2]) * 1024
                        else:
                            memory_usage += float(mem_str) / (1024 * 1024)

            return {'cpu_usage': cpu_usage, 'memory_usage': memory_usage}

        except Exception:
            logger.exception("Failed to fetch metrics for pod %s in %s", pod_name, namespace)
            return {'cpu_usage': 0.0, 'memory_usage': 0.0}

    def test_connection(self):
        """Test the connection to the Kubernetes cluster"""
        try:
            self.v1.list_namespace()
            return True
        except Exception:
            return False
