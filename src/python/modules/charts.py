"""
Chart creation functions for Spark Pod Resource Monitor
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def create_resource_chart(pod_data, title):
    """Create resource utilization chart"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('CPU Usage vs Limits', 'Memory Usage vs Limits',
                       'CPU Utilization %', 'Memory Utilization %'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"type": "indicator"}, {"type": "indicator"}]]
    )

    # CPU bar chart
    fig.add_trace(
        go.Bar(name='CPU Request', x=['CPU'], y=[pod_data['cpu_request']],
               marker_color='lightblue', opacity=0.7),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(name='CPU Limit', x=['CPU'], y=[pod_data['cpu_limit']],
               marker_color='blue', opacity=0.7),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(name='CPU Usage', x=['CPU'], y=[pod_data['cpu_usage']],
               marker_color='red'),
        row=1, col=1
    )

    # Memory bar chart (MiB)
    fig.add_trace(
        go.Bar(name='Memory Request (MiB)', x=['Memory'], y=[pod_data['memory_request']],
               marker_color='lightgreen', opacity=0.7, showlegend=False),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(name='Memory Limit (MiB)', x=['Memory'], y=[pod_data['memory_limit']],
               marker_color='green', opacity=0.7, showlegend=False),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(name='Memory Usage (MiB)', x=['Memory'], y=[pod_data['memory_usage']],
               marker_color='orange', showlegend=False),
        row=1, col=2
    )

    # CPU utilization gauge
    limit_cpu = max(pod_data['cpu_limit'], 0.0)
    cpu_util = (pod_data['cpu_usage'] / (limit_cpu if limit_cpu > 0 else 0.1)) * 100
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=cpu_util,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "CPU %"},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "red" if cpu_util > 80 else "orange" if cpu_util > 60 else "green"},
                'steps': [
                    {'range': [0, 60], 'color': "lightgray"},
                    {'range': [60, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "lightcoral"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ),
        row=2, col=1
    )

    # Memory utilization gauge
    limit_mem = max(pod_data['memory_limit'], 0.0)
    mem_util = (pod_data['memory_usage'] / (limit_mem if limit_mem > 0 else 1)) * 100
    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=mem_util,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Memory %"},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "red" if mem_util > 80 else "orange" if mem_util > 60 else "green"},
                'steps': [
                    {'range': [0, 60], 'color': "lightgray"},
                    {'range': [60, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "lightcoral"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ),
        row=2, col=2
    )

    fig.update_layout(
        title=title,
        height=600,
        showlegend=True
    )

    return fig


def create_historical_timeline_chart(historical_df, pod_name):
    """Create timeline chart showing pod resource usage over time"""
    if historical_df.empty:
        return None

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        subplot_titles=['CPU Usage Over Time', 'Memory Usage Over Time'],
        vertical_spacing=0.1
    )

    # Convert timestamp to datetime
    historical_df['timestamp'] = pd.to_datetime(historical_df['timestamp'])

    # CPU timeline
    fig.add_trace(
        go.Scatter(x=historical_df['timestamp'], y=historical_df['cpu_usage'],
                  mode='lines+markers', name='CPU Usage', line=dict(color='red')),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=historical_df['timestamp'], y=historical_df['cpu_limit'],
                  mode='lines', name='CPU Limit', line=dict(color='blue', dash='dash')),
        row=1, col=1
    )

    # Memory timeline
    fig.add_trace(
        go.Scatter(x=historical_df['timestamp'], y=historical_df['memory_usage'],
                  mode='lines+markers', name='Memory Usage (MiB)', line=dict(color='orange')),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=historical_df['timestamp'], y=historical_df['memory_limit'],
                  mode='lines', name='Memory Limit (MiB)', line=dict(color='green', dash='dash')),
        row=2, col=1
    )

    fig.update_layout(
        title=f'Resource Usage Timeline - {pod_name}',
        height=600,
        showlegend=True,
        xaxis_title="Time"
    )

    fig.update_yaxes(title_text="CPU Cores", row=1, col=1)
    fig.update_yaxes(title_text="Memory (MiB)", row=2, col=1)

    return fig


def create_application_summary_chart(historical_df):
    """Create application summary chart"""
    if historical_df.empty:
        return None

    app_summary = historical_df.groupby('app_name').agg({
        'cpu_usage': 'mean',
        'memory_usage': 'mean',
        'pod_name': 'count'
    }).round(2)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=['Average Resource Usage by Application', 'Pod Count by Application']
    )

    # Resource usage chart
    fig.add_trace(
        go.Bar(x=app_summary.index, y=app_summary['cpu_usage'],
               name='Avg CPU Usage', marker_color='blue'),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(x=app_summary.index, y=app_summary['memory_usage'],
               name='Avg Memory Usage (MiB)', marker_color='orange'),
        row=1, col=1
    )

    # Pod count chart
    fig.add_trace(
        go.Bar(x=app_summary.index, y=app_summary['pod_name'],
               name='Pod Count', marker_color='green'),
        row=1, col=2
    )

    fig.update_layout(
        title="Application Resource Summary",
        height=400,
        showlegend=True
    )

    return fig
