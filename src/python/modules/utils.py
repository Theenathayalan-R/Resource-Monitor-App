"""
Utility functions for Spark Pod Resource Monitor
"""


def parse_cpu_quantity(quantity_str):
    """Parse Kubernetes CPU quantity string to cores (float)."""
    if not quantity_str:
        return 0.0
    s = str(quantity_str)
    if s.endswith('m'):
        return float(s[:-1]) / 1000.0
    if s.endswith('n'):
        return float(s[:-1]) / 1_000_000_000.0
    # If no suffix, treat as cores
    return float(s)


def parse_memory_quantity(quantity_str):
    """Parse Kubernetes memory quantity string to MiB (float)."""
    if not quantity_str:
        return 0.0
    s = str(quantity_str)
    unit_multipliers = {
        'Ki': 1 / 1024.0,  # KiB to MiB
        'Mi': 1.0,
        'Gi': 1024.0,
        'Ti': 1024.0 * 1024.0,
        'K': 1 / 1024.0,
        'M': 1.0,
        'G': 1024.0,
        'T': 1024.0 * 1024.0,
    }
    for unit, factor in unit_multipliers.items():
        if s.endswith(unit):
            return float(s[:-len(unit)]) * factor
    # If plain number with no unit, assume bytes and convert to MiB
    try:
        return float(s) / (1024.0 * 1024.0)
    except ValueError:
        return 0.0


def parse_resource_quantity(quantity_str):
    """Backward-compatible parser; detects CPU suffixes; known memory suffixes to MiB; else numeric as-is."""
    if not quantity_str:
        return 0
    s = str(quantity_str)
    # CPU hints
    if s.endswith('m') or s.endswith('n'):
        return parse_cpu_quantity(s)
    # Known memory suffixes
    for suf in ('Ki', 'Mi', 'Gi', 'Ti', 'K', 'M', 'G', 'T'):
        if s.endswith(suf):
            return parse_memory_quantity(s)
    # Fallback: numeric as-is (backward compatibility with tests expecting 2 -> 2.0)
    try:
        return float(s)
    except ValueError:
        return 0


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
    """Extract resource requests and limits (CPU cores, Memory MiB)."""
    containers = pod.spec.containers
    total_cpu_request = 0.0
    total_cpu_limit = 0.0
    total_memory_request = 0.0
    total_memory_limit = 0.0

    for container in containers:
        resources = container.resources
        if getattr(resources, 'requests', None):
            total_cpu_request += parse_cpu_quantity(resources.requests.get('cpu', '0'))
            total_memory_request += parse_memory_quantity(resources.requests.get('memory', '0'))

        if getattr(resources, 'limits', None):
            total_cpu_limit += parse_cpu_quantity(resources.limits.get('cpu', '0'))
            total_memory_limit += parse_memory_quantity(resources.limits.get('memory', '0'))

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
        return 0.0 if default_limit <= 0 else (usage / default_limit) * 100
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
