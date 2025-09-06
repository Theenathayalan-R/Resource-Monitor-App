"""
Mock data generators for Spark Pod Resource Monitor (offline demo mode)
"""
from types import SimpleNamespace as NS
from datetime import datetime, timedelta
import random


def _mock_container(cpu_req="500m", cpu_lim="1", mem_req="1024Mi", mem_lim="2048Mi"):
    resources = NS(
        requests={"cpu": cpu_req, "memory": mem_req},
        limits={"cpu": cpu_lim, "memory": mem_lim},
    )
    return NS(resources=resources)


def _mock_pod(name, pod_type, app_name, node_name, phase="Running", restarts=0, created=None, labels=None, annotations=None):
    labels = labels or {"spark-role": pod_type, "app": app_name}
    annotations = annotations or {}
    created = created or (datetime.now() - timedelta(minutes=random.randint(5, 120)))

    metadata = NS(
        name=name,
        labels=labels,
        annotations=annotations,
        creation_timestamp=created,
    )

    spec = NS(
        node_name=node_name,
        containers=[_mock_container()],
    )

    status = NS(
        phase=phase,
        container_statuses=[NS(restart_count=restarts)],
    )

    return NS(metadata=metadata, spec=spec, status=status)


def generate_mock_pods(namespace: str, drivers: int = 1, executors_per_driver: int = 3):
    """Generate a list of mock driver and executor pods for demo purposes.

    Returns: (pods, drivers_list, executors_list)
    """
    random.seed(42)
    pods = []
    drivers_list = []
    executors_list = []

    for d in range(1, drivers + 1):
        app = f"spark-app-{d}"
        driver_name = f"{app}-driver"
        driver = _mock_pod(driver_name, "driver", app, node_name=f"node-{d}")
        pods.append(driver)
        drivers_list.append(driver)

        for e in range(1, executors_per_driver + 1):
            exec_name = f"{app}-exec-{e}"
            exec_pod = _mock_pod(exec_name, "executor", app, node_name=f"node-{(d+e)%3+1}")
            pods.append(exec_pod)
            executors_list.append(exec_pod)

    return pods, drivers_list, executors_list


def generate_mock_metrics(pods):
    """Generate a metrics map for the provided mock pods: {pod_name: {cpu_usage, memory_usage}}
    CPU usage in cores (float), memory in MiB (float).
    """
    random.seed(99)
    metrics = {}
    for pod in pods:
        # CPU between 0.1 and 0.9 cores
        cpu = round(random.uniform(0.1, 0.9), 3)
        # Memory between 256 and 2048 MiB
        mem = float(random.randint(256, 2048))
        metrics[pod.metadata.name] = {"cpu_usage": cpu, "memory_usage": mem}
    return metrics
