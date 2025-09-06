"""
Current Status view: live pod and metrics display, with optional demo mode.
"""
import time
from datetime import datetime
import pandas as pd
import streamlit as st

from utils import (
    classify_spark_pods,
    get_pod_resources,
    extract_app_name,
    format_resource_value,
    calculate_utilization,
)
from mock_data import generate_mock_pods, generate_mock_metrics
from kubernetes_client import KubernetesClient


def render_current_status(namespace: str, api_server_url: str, token: str | None, history_manager, demo_mode: bool, refresh_interval: int, auto_refresh: bool, pod_age_hours: int = 6):
    if not token and not demo_mode:
        st.warning("Please provide a valid token to use Current Status mode, or enable 'Use mock data (demo)'.")
        return

    pods = []
    drivers = []
    executors = []
    metrics_map = {}

    if demo_mode:
        st.info("Demo mode active: displaying mock Spark driver and executor pods.")
        pods, drivers, executors = generate_mock_pods(namespace, drivers=2, executors_per_driver=3)
        metrics_map = generate_mock_metrics(pods)
    else:
        # Show filter status
        if pod_age_hours < 24:
            st.info(f"🔍 Filtering to show only pods started in the last {pod_age_hours} hours")
        else:
            days = pod_age_hours // 24
            st.info(f"🔍 Filtering to show only pods started in the last {days} day{'s' if days > 1 else ''}")
        
        # Initialize Kubernetes client
        if (token is not None) and ('k8s_client' not in st.session_state or st.sidebar.button("Reconnect")):
            with st.spinner("Connecting to cluster..."):
                try:
                    st.session_state.k8s_client = KubernetesClient(api_server_url, str(token))
                    st.success("Successfully connected to the cluster!")
                except Exception as e:
                    st.error(f"Failed to connect to the cluster: {str(e)}")
                    return

        k8s_client = st.session_state.get('k8s_client')
        if k8s_client is None:
            st.error("Cluster client not initialized. Please provide a valid token or enable demo mode.")
            return

        # Fetch and store current pods data
        start_time = time.time()
        with st.spinner(f"Fetching pods started in last {pod_age_hours} hours and storing history..."):
            try:
                pods = k8s_client.get_pods(namespace, max_age_hours=pod_age_hours)
                drivers, executors = classify_spark_pods(pods)

                # Batch metrics retrieval for namespace
                metrics_map = k8s_client.get_namespace_pod_metrics(namespace)
                metrics_available = bool(metrics_map)
                if not metrics_available:
                    st.warning("Metrics API unavailable; showing zeros for usage values.")
            except Exception as e:
                st.error(f"Error fetching pod data: {str(e)}")
                return

    # Store to database (works for both demo and real data)
    start_time = time.time()
    with st.spinner("Updating local history database..."):
        try:
            batch_items = []
            active_pod_names = []
            for pod in pods:
                app_name = extract_app_name(pod.metadata.name)
                pod_type = 'driver' if pod in drivers else 'executor' if pod in executors else 'unknown'

                if pod_type != 'unknown':
                    resources = get_pod_resources(pod)
                    m = metrics_map.get(pod.metadata.name, {'cpu_usage': 0.0, 'memory_usage': 0.0})
                    batch_items.append((
                        namespace, pod.metadata.name, pod_type, app_name, pod.status.phase,
                        resources['cpu_request'], resources['cpu_limit'], m['cpu_usage'],
                        resources['memory_request'], resources['memory_limit'], m['memory_usage'],
                        getattr(pod.spec, 'node_name', None), getattr(pod.metadata, 'creation_timestamp', None),
                        dict(pod.metadata.labels or {}), dict(pod.metadata.annotations or {}),
                        sum(getattr(cs, 'restart_count', 0) for cs in (getattr(pod.status, 'container_statuses', []) or []))
                    ))
                    active_pod_names.append(pod.metadata.name)

            if batch_items:
                history_manager.store_pod_data_batch(batch_items)
            history_manager.mark_pods_inactive(namespace, active_pod_names)
        except Exception as e:
            st.error(f"Database update failed: {str(e)}")
            return

    fetch_duration = time.time() - start_time

    # Display current status
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Pods", len(pods))
    with col2:
        st.metric("Driver Pods", len(drivers))
    with col3:
        st.metric("Executor Pods", len(executors))
    with col4:
        st.metric("Last Updated", datetime.now().strftime("%H:%M:%S"))
    with col5:
        st.metric("Fetch Duration", f"{fetch_duration:.2f}s")

    # Driver pods overview
    if drivers:
        st.header("Spark Driver Pods")

        driver_data = []
        for driver in drivers:
            resources = get_pod_resources(driver)
            m = metrics_map.get(driver.metadata.name, {'cpu_usage': 0.0, 'memory_usage': 0.0})

            driver_data.append({
                'Driver Name': driver.metadata.name,
                'Status': driver.status.phase,
                'CPU Request': format_resource_value(resources['cpu_request'], 'cpu'),
                'CPU Limit': format_resource_value(resources['cpu_limit'], 'cpu'),
                'CPU Usage': format_resource_value(m['cpu_usage'], 'cpu'),
                'Memory Request (MiB)': format_resource_value(resources['memory_request'], 'memory'),
                'Memory Limit (MiB)': format_resource_value(resources['memory_limit'], 'memory'),
                'Memory Usage (MiB)': format_resource_value(m['memory_usage'], 'memory'),
                'Created': driver.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S") if driver.metadata.creation_timestamp else "Unknown"
            })

        driver_df = pd.DataFrame(driver_data)
        st.dataframe(driver_df, use_container_width=True)

        # Driver selection for detailed view
        selected_driver = st.selectbox(
            "Select Driver for Detailed View",
            options=[d['Driver Name'] for d in driver_data],
            key="driver_select"
        )

        if selected_driver:
            selected_driver_obj = next(d for d in drivers if d.metadata.name == selected_driver)

            st.subheader(f"Driver Details: {selected_driver}")

            # Get detailed info
            resources = get_pod_resources(selected_driver_obj)
            m = metrics_map.get(selected_driver, {'cpu_usage': 0.0, 'memory_usage': 0.0})

            chart_data = {**resources, **m}

            # Create detailed chart
            from charts import create_resource_chart
            fig = create_resource_chart(chart_data, f"Resource Utilization - {selected_driver}")
            st.plotly_chart(fig, use_container_width=True)

            # Find associated executors
            driver_app_name = extract_app_name(selected_driver)
            associated_executors = [e for e in executors if extract_app_name(e.metadata.name) == driver_app_name]

            if associated_executors:
                st.subheader(f"Associated Executors ({len(associated_executors)})")

                executor_data = []
                for executor in associated_executors:
                    exec_resources = get_pod_resources(executor)
                    exec_m = metrics_map.get(executor.metadata.name, {'cpu_usage': 0.0, 'memory_usage': 0.0})

                    cpu_util = calculate_utilization(exec_m['cpu_usage'], exec_resources['cpu_limit']) if exec_resources['cpu_limit'] > 0 else 0.0
                    mem_util = calculate_utilization(exec_m['memory_usage'], exec_resources['memory_limit'], 1) if exec_resources['memory_limit'] > 0 else 0.0

                    executor_data.append({
                        'Executor Name': executor.metadata.name,
                        'Status': executor.status.phase,
                        'CPU Usage': format_resource_value(exec_m['cpu_usage'], 'cpu'),
                        'CPU Request': format_resource_value(exec_resources['cpu_request'], 'cpu'),
                        'CPU Limit': format_resource_value(exec_resources['cpu_limit'], 'cpu'),
                        'Memory Usage (MiB)': format_resource_value(exec_m['memory_usage'], 'memory'),
                        'Memory Request (MiB)': format_resource_value(exec_resources['memory_request'], 'memory'),
                        'Memory Limit (MiB)': format_resource_value(exec_resources['memory_limit'], 'memory'),
                        'CPU Utilization %': f"{cpu_util:.1f}%" if exec_resources['cpu_limit'] > 0 else 'N/A',
                        'Memory Utilization %': f"{mem_util:.1f}%" if exec_resources['memory_limit'] > 0 else 'N/A'
                    })

                executor_df = pd.DataFrame(executor_data)
                st.dataframe(executor_df, use_container_width=True)
    else:
        st.info("No Spark driver pods found in the specified namespace.")

    # Auto-refresh for current status mode
    if auto_refresh:
        autorefresh_fn = getattr(st, 'autorefresh', None)
        if callable(autorefresh_fn):
            autorefresh_fn(interval=refresh_interval * 1000, key="auto_refresh_timer")
        # else: no-op fallback
