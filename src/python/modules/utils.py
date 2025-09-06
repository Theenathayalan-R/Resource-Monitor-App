"""
Utility functions for Spark Pod Resource Monitor
"""


def parse_resource_quantity(quantity_str):
    """Parse Kubernetes resource quantity string to numeric value"""
    if not quantity_str:
        return 0

    if quantity_str.endswith('m'):
        return float(quantity_str[:-1]) / 1000
    elif quantity_str.endswith('n'):
        return float(quantity_str[:-1]) / 1000000000

    unit_multipliers = {
        'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3,
        'K': 1000, 'M': 1000**2, 'G': 1000**3
    }

    for unit, multiplier in unit_multipliers.items():
        if quantity_str.endswith(unit):
            return float(quantity_str[:-len(unit)]) * multiplier / (1024**2)

    return float(quantity_str)


def classify_spark_pods(pods):
    """Classify pods as driver or executor pods"""
    drivers = []
    executors = []

    for pod in pods:
        pod_name = pod.metadata.name
        labels = pod.metadata.labels or {}

        if labels.get('spark-role') == 'driver' or 'driver' in pod_name.lower():
            drivers.append(pod)
        elif labels.get('spark-role') == 'executor' or 'exec' in pod_name.lower():
            executors.append(pod)
        elif 'spark' in pod_name.lower():
            if any(x in pod_name.lower() for x in ['driver', 'master']):
                drivers.append(pod)
            elif any(x in pod_name.lower() for x in ['exec', 'worker']):
                executors.append(pod)

    return drivers, executors


def get_pod_resources(pod):
    """Extract resource requests, limits and current usage"""
    containers = pod.spec.containers
    total_cpu_request = 0
    total_cpu_limit = 0
    total_memory_request = 0
    total_memory_limit = 0

    for container in containers:
        resources = container.resources
        if resources.requests:
            total_cpu_request += parse_resource_quantity(resources.requests.get('cpu', '0'))
            total_memory_request += parse_resource_quantity(resources.requests.get('memory', '0'))

        if resources.limits:
            total_cpu_limit += parse_resource_quantity(resources.limits.get('cpu', '0'))
            total_memory_limit += parse_resource_quantity(resources.limits.get('memory', '0'))

    return {
        'cpu_request': total_cpu_request,
        'cpu_limit': total_cpu_limit,
        'memory_request': total_memory_request,
        'memory_limit': total_memory_limit
    }


def extract_app_name(pod_name):
    """Extract Spark application name from pod name"""
    # Common patterns: app-name-driver, app-name-exec-1, spark-app-driver-xxx
    if '-driver' in pod_name:
        return pod_name.split('-driver')[0]
    elif '-exec' in pod_name:
        return pod_name.split('-exec')[0]
    elif 'executor' in pod_name:
        return pod_name.split('-executor')[0]
    else:
        # Fallback: return the full pod name if no pattern matches
        return pod_name


def format_resource_value(value, resource_type='cpu'):
    """Format resource values for display"""
    try:
        if resource_type == 'cpu':
            return f"{float(value):.2f}"
        elif resource_type == 'memory':
            return f"{float(value):.0f}"
        return str(value)
    except (ValueError, TypeError):
        return str(value)


def calculate_utilization(usage, limit, default_limit=0.1):
    """Calculate resource utilization percentage"""
    if limit <= 0:
        limit = default_limit
    return (usage / limit) * 100


def get_status_color(status):
    """Get color for pod status"""
    status_colors = {
        'Running': 'green',
        'Pending': 'yellow',
        'Succeeded': 'blue',
        'Failed': 'red',
        'Unknown': 'gray'
    }
    return status_colors.get(status, 'gray')
