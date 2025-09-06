"""
Unit tests for utils module
"""
import unittest
from unittest.mock import Mock
from modules.utils import (
    parse_resource_quantity,
    classify_spark_pods,
    get_pod_resources,
    extract_app_name,
    format_resource_value,
    calculate_utilization,
    get_status_color
)


class TestUtils(unittest.TestCase):

    def test_parse_resource_quantity(self):
        """Test parsing of Kubernetes resource quantities"""
        # Test CPU units
        self.assertEqual(parse_resource_quantity('1000m'), 1.0)
        self.assertEqual(parse_resource_quantity('500m'), 0.5)
        self.assertEqual(parse_resource_quantity('2'), 2.0)

        # Test memory units
        self.assertEqual(parse_resource_quantity('1Gi'), 1024.0)
        self.assertEqual(parse_resource_quantity('512Mi'), 512.0)
        self.assertEqual(parse_resource_quantity('1024Ki'), 1.0)

        # Test edge cases
        self.assertEqual(parse_resource_quantity(''), 0)
        self.assertEqual(parse_resource_quantity(None), 0)

    def test_classify_spark_pods(self):
        """Test classification of Spark pods"""
        # Create mock pods
        driver_pod = Mock()
        driver_pod.metadata.name = 'spark-app-driver'
        driver_pod.metadata.labels = {'spark-role': 'driver'}

        executor_pod = Mock()
        executor_pod.metadata.name = 'spark-app-exec-1'
        executor_pod.metadata.labels = {'spark-role': 'executor'}

        regular_pod = Mock()
        regular_pod.metadata.name = 'nginx-pod'
        regular_pod.metadata.labels = {}

        pods = [driver_pod, executor_pod, regular_pod]
        drivers, executors = classify_spark_pods(pods)

        self.assertEqual(len(drivers), 1)
        self.assertEqual(len(executors), 1)
        self.assertEqual(drivers[0], driver_pod)
        self.assertEqual(executors[0], executor_pod)

    def test_get_pod_resources(self):
        """Test extraction of pod resources"""
        # Create mock pod
        pod = Mock()
        container = Mock()
        resources = Mock()

        # Mock requests
        resources.requests = {'cpu': '1000m', 'memory': '1Gi'}
        # Mock limits
        resources.limits = {'cpu': '2000m', 'memory': '2Gi'}
        container.resources = resources
        pod.spec.containers = [container]

        result = get_pod_resources(pod)

        self.assertEqual(result['cpu_request'], 1.0)
        self.assertEqual(result['cpu_limit'], 2.0)
        self.assertEqual(result['memory_request'], 1024.0)
        self.assertEqual(result['memory_limit'], 2048.0)

    def test_extract_app_name(self):
        """Test extraction of application name from pod name"""
        test_cases = [
            ('my-app-driver', 'my-app'),
            ('spark-job-exec-1', 'spark-job'),
            ('app-executor-123', 'app'),
            ('single-pod', 'single-pod'),
            ('complex-app-name-driver-extra', 'complex-app-name')
        ]

        for pod_name, expected in test_cases:
            with self.subTest(pod_name=pod_name):
                self.assertEqual(extract_app_name(pod_name), expected)

    def test_format_resource_value(self):
        """Test formatting of resource values"""
        self.assertEqual(format_resource_value(1.5, 'cpu'), '1.50')
        self.assertEqual(format_resource_value(1024, 'memory'), '1024')
        self.assertEqual(format_resource_value('test', 'cpu'), 'test')

    def test_calculate_utilization(self):
        """Test calculation of resource utilization"""
        self.assertEqual(calculate_utilization(50, 100), 50.0)
        self.assertEqual(calculate_utilization(1, 2), 50.0)
        self.assertEqual(calculate_utilization(0, 0), 0.0)  # Test with default limit

    def test_get_status_color(self):
        """Test status color mapping"""
        self.assertEqual(get_status_color('Running'), 'green')
        self.assertEqual(get_status_color('Pending'), 'yellow')
        self.assertEqual(get_status_color('Failed'), 'red')
        self.assertEqual(get_status_color('Unknown'), 'gray')
        self.assertEqual(get_status_color('NonExistent'), 'gray')


if __name__ == '__main__':
    unittest.main()
