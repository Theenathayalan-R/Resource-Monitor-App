"""
Kubernetes client operations for Spark Pod Resource Monitor
"""
import tempfile
import os
import yaml
from kubernetes import client, config
from kubernetes.client.rest import ApiException


class KubernetesClient:
    def __init__(self, api_server_url, kubeconfig_token):
        self.api_server_url = api_server_url
        self.kubeconfig_token = kubeconfig_token
        self.v1 = None
        self.metrics_client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Kubernetes client with provided credentials"""
        try:
            kubeconfig_content = {
                'apiVersion': 'v1',
                'kind': 'Config',
                'clusters': [{
                    'name': 'openshift-cluster',
                    'cluster': {
                        'server': self.api_server_url,
                        'insecure-skip-tls-verify': True
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

            os.unlink(kubeconfig_path)

        except Exception as e:
            raise Exception(f"Failed to initialize Kubernetes client: {str(e)}")

    def get_pods(self, namespace):
        """Get all pods in the specified namespace"""
        try:
            pods = self.v1.list_namespaced_pod(namespace=namespace)
            return pods.items
        except ApiException as e:
            raise Exception(f"Error fetching pods: {e}")

    def get_pod_metrics(self, namespace, pod_name):
        """Get pod metrics (CPU, Memory usage) using Kubernetes Metrics API"""
        try:
            from kubernetes.client import CustomObjectsApi

            # Initialize metrics client if not already done
            if not self.metrics_client:
                self.metrics_client = CustomObjectsApi(self.v1.api_client)

            # Get pod metrics
            metrics = self.metrics_client.get_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=namespace,
                plural="pods",
                name=pod_name
            )

            cpu_usage = 0
            memory_usage = 0

            if 'containers' in metrics:
                for container in metrics['containers']:
                    if 'usage' in container:
                        # Parse CPU usage
                        if 'cpu' in container['usage']:
                            cpu_str = container['usage']['cpu']
                            if cpu_str.endswith('n'):
                                cpu_usage += float(cpu_str[:-1]) / 1000000000  # nanocores to cores
                            elif cpu_str.endswith('m'):
                                cpu_usage += float(cpu_str[:-1]) / 1000  # millicores to cores
                            else:
                                cpu_usage += float(cpu_str)
                        else:
                            cpu_usage += 0

                        # Parse memory usage
                        if 'memory' in container['usage']:
                            mem_str = container['usage']['memory']
                            if mem_str.endswith('Ki'):
                                memory_usage += float(mem_str[:-2]) / 1024  # KiB to MiB
                            elif mem_str.endswith('Mi'):
                                memory_usage += float(mem_str[:-2])  # Already in MiB
                            elif mem_str.endswith('Gi'):
                                memory_usage += float(mem_str[:-2]) * 1024  # GiB to MiB
                            else:
                                memory_usage += float(mem_str) / (1024 * 1024)  # bytes to MiB
                        else:
                            memory_usage += 0

            return {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage
            }

        except Exception as e:
            # Return zero values if metrics are not available
            return {'cpu_usage': 0, 'memory_usage': 0}

    def test_connection(self):
        """Test the connection to the Kubernetes cluster"""
        try:
            self.v1.list_namespace()
            return True
        except Exception:
            return False
