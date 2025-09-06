"""
Database operations for Spark Pod Resource Monitor
"""
import sqlite3
import pandas as pd
import json
from datetime import datetime
from .config import DB_PATH, HISTORY_RETENTION_DAYS


class HistoryManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_database()

    def _connect(self):
        """Create a SQLite connection with WAL and busy timeout enabled."""
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA busy_timeout=5000;')
        return conn

    def init_database(self):
        """Initialize SQLite database for storing pod history"""
        with self._connect() as conn:
            cursor = conn.cursor()

            # Create pods table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pod_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    namespace TEXT,
                    pod_name TEXT,
                    pod_type TEXT, -- 'driver' or 'executor'
                    app_name TEXT,
                    status TEXT,
                    cpu_request REAL,
                    cpu_limit REAL,
                    cpu_usage REAL,
                    memory_request REAL,
                    memory_limit REAL,
                    memory_usage REAL,
                    node_name TEXT,
                    creation_timestamp DATETIME,
                    deletion_timestamp DATETIME,
                    labels TEXT, -- JSON string
                    annotations TEXT, -- JSON string
                    container_restarts INTEGER,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')

            # Create events table for pod lifecycle events
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pod_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    namespace TEXT,
                    pod_name TEXT,
                    event_type TEXT, -- 'created', 'running', 'terminated', 'failed'
                    event_reason TEXT,
                    event_message TEXT,
                    app_name TEXT
                )
            ''')

            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pod_name ON pod_history(pod_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON pod_history(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_app_name ON pod_history(app_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pod_type ON pod_history(pod_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ns_ts ON pod_history(namespace, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ns_pod ON pod_history(namespace, pod_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_ns_active ON pod_history(namespace, is_active)')

    def _to_iso(self, dt):
        if dt is None:
            return None
        try:
            return dt.isoformat(sep=' ', timespec='seconds')
        except Exception:
            return str(dt)

    def store_pod_data(self, namespace, pod, pod_type, app_name, resources, metrics):
        """Store current pod data"""
        labels_json = json.dumps(dict(pod.metadata.labels or {}))
        annotations_json = json.dumps(dict(pod.metadata.annotations or {}))

        # Count container restarts
        restart_count = 0
        if getattr(pod.status, 'container_statuses', None):
            restart_count = sum(getattr(cs, 'restart_count', 0) for cs in pod.status.container_statuses)

        creation_ts = self._to_iso(getattr(pod.metadata, 'creation_timestamp', None))

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pod_history
                (namespace, pod_name, pod_type, app_name, status,
                 cpu_request, cpu_limit, cpu_usage,
                 memory_request, memory_limit, memory_usage,
                 node_name, creation_timestamp, labels, annotations,
                 container_restarts, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', (
                namespace, pod.metadata.name, pod_type, app_name, pod.status.phase,
                resources['cpu_request'], resources['cpu_limit'], metrics['cpu_usage'],
                resources['memory_request'], resources['memory_limit'], metrics['memory_usage'],
                getattr(pod.spec, 'node_name', None), creation_ts,
                labels_json, annotations_json, restart_count
            ))

    def store_pod_data_batch(self, items):
        """Batch insert pod history records.
        items: list of tuples (namespace, pod_name, pod_type, app_name, status,
        cpu_request, cpu_limit, cpu_usage, memory_request, memory_limit, memory_usage,
        node_name, creation_timestamp, labels, annotations, container_restarts)
        """
        def normalize(item):
            (namespace, pod_name, pod_type, app_name, status,
             cpu_req, cpu_lim, cpu_use, mem_req, mem_lim, mem_use,
             node_name, creation_ts, labels, annotations, restarts) = item
            # Ensure JSON strings for labels/annotations
            if not isinstance(labels, str):
                labels = json.dumps(labels or {})
            if not isinstance(annotations, str):
                annotations = json.dumps(annotations or {})
            # Ensure ISO datetime for creation_ts
            creation_ts = self._to_iso(creation_ts)
            return (namespace, pod_name, pod_type, app_name, status,
                    cpu_req, cpu_lim, cpu_use, mem_req, mem_lim, mem_use,
                    node_name, creation_ts, labels, annotations, restarts)

        norm_items = [normalize(i) for i in items]
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO pod_history
                (namespace, pod_name, pod_type, app_name, status,
                 cpu_request, cpu_limit, cpu_usage,
                 memory_request, memory_limit, memory_usage,
                 node_name, creation_timestamp, labels, annotations,
                 container_restarts, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', norm_items)

    def mark_pods_inactive(self, namespace, active_pod_names):
        """Mark pods as inactive if they're no longer running"""
        with self._connect() as conn:
            cursor = conn.cursor()

            if active_pod_names:
                placeholders = ','.join('?' * len(active_pod_names))
                cursor.execute(f'''
                    UPDATE pod_history
                    SET is_active = 0, deletion_timestamp = CURRENT_TIMESTAMP
                    WHERE namespace = ? AND is_active = 1
                    AND pod_name NOT IN ({placeholders})
                ''', [namespace] + active_pod_names)
            else:
                cursor.execute('''
                    UPDATE pod_history
                    SET is_active = 0, deletion_timestamp = CURRENT_TIMESTAMP
                    WHERE namespace = ? AND is_active = 1
                ''', (namespace,))

    def log_pod_event(self, namespace, pod_name, event_type, reason, message, app_name):
        """Log pod lifecycle events"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pod_events
                (namespace, pod_name, event_type, event_reason, event_message, app_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (namespace, pod_name, event_type, reason, message, app_name))

    def get_historical_data(self, namespace, hours_back=48, app_name=None):
        """Get historical pod data"""
        with self._connect() as conn:
            base_query = '''
                SELECT * FROM pod_history
                WHERE namespace = ?
                AND timestamp >= datetime('now', '-{} hours')
            '''.format(hours_back)

            params = [namespace]

            if app_name:
                base_query += ' AND app_name = ?'
                params.append(app_name)

            base_query += ' ORDER BY timestamp DESC'

            df = pd.read_sql_query(base_query, conn, params=params)
            return df

    def get_pod_timeline(self, namespace, pod_name):
        """Get timeline for a specific pod"""
        with self._connect() as conn:
            # Get pod data timeline
            pod_df = pd.read_sql_query('''
                SELECT * FROM pod_history
                WHERE namespace = ? AND pod_name = ?
                ORDER BY timestamp
            ''', conn, params=(namespace, pod_name))

            # Get pod events timeline
            events_df = pd.read_sql_query('''
                SELECT * FROM pod_events
                WHERE namespace = ? AND pod_name = ?
                ORDER BY timestamp
            ''', conn, params=(namespace, pod_name))

            return pod_df, events_df

    def cleanup_old_data(self, retention_days=HISTORY_RETENTION_DAYS):
        """Clean up data older than retention period"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM pod_history
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(retention_days))
            cursor.execute('''
                DELETE FROM pod_events
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(retention_days))

    def export_historical_data(self, namespace, start_date, end_date, format='json'):
        """Export historical data for backup/analysis"""
        # Ensure inclusive end of day by appending 23:59:59
        start_dt = f"{start_date} 00:00:00" if len(start_date) == 10 else start_date
        end_dt = f"{end_date} 23:59:59" if len(end_date) == 10 else end_date

        with self._connect() as conn:
            df = pd.read_sql_query('''
                SELECT * FROM pod_history
                WHERE namespace = ?
                AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
            ''', conn, params=(namespace, start_dt, end_dt))

        if format == 'json':
            return df.to_json(orient='records', date_format='iso')
        elif format == 'csv':
            return df.to_csv(index=False)
        else:
            return df

    def get_database_stats(self):
        """Get database statistics"""
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM pod_history")
            total_records = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM pod_events")
            total_events = cursor.fetchone()[0]

            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM pod_history")
            date_range = cursor.fetchone()

        return {
            'total_records': total_records,
            'total_events': total_events,
            'date_range': date_range
        }
