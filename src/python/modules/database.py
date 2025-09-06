"""
Database operations for Spark Pod Resource Monitor
"""
import sqlite3
import pandas as pd
import json
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from contextlib import contextmanager
from config import DB_PATH, HISTORY_RETENTION_DAYS, MAX_DB_CONNECTIONS
from logging_config import DatabaseError, log_performance
from performance import monitor_performance, DatabaseConnectionPool, get_performance_monitor
from validation import sanitize_pod_name

logger = logging.getLogger(__name__)


class HistoryManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.connection_pool = DatabaseConnectionPool(db_path, MAX_DB_CONNECTIONS)
        self.init_database()
        logger.info(f"HistoryManager initialized with database: {db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections with proper error handling"""
        conn = None
        try:
            conn = self.connection_pool.get_connection()
            if conn is None:
                raise DatabaseError("Could not obtain database connection from pool")
            
            # Record database operation for performance monitoring
            get_performance_monitor().record_db_operation()
            
            yield conn
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {str(e)}", exc_info=True)
            raise DatabaseError(f"Database operation failed: {str(e)}") from e
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Unexpected error in database operation: {str(e)}", exc_info=True)
            raise DatabaseError(f"Unexpected database error: {str(e)}") from e
        finally:
            if conn:
                try:
                    conn.commit()
                    self.connection_pool.return_connection(conn)
                except Exception as e:
                    logger.warning(f"Error returning connection to pool: {str(e)}")

    @monitor_performance("database")
    def init_database(self):
        """Initialize SQLite database for storing pod history"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Create pods table with better constraints
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS pod_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        namespace TEXT NOT NULL,
                        pod_name TEXT NOT NULL,
                        pod_type TEXT NOT NULL CHECK (pod_type IN ('driver', 'executor')),
                        app_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        cpu_request REAL DEFAULT 0.0 CHECK (cpu_request >= 0),
                        cpu_limit REAL DEFAULT 0.0 CHECK (cpu_limit >= 0),
                        cpu_usage REAL DEFAULT 0.0 CHECK (cpu_usage >= 0),
                        memory_request REAL DEFAULT 0.0 CHECK (memory_request >= 0),
                        memory_limit REAL DEFAULT 0.0 CHECK (memory_limit >= 0),
                        memory_usage REAL DEFAULT 0.0 CHECK (memory_usage >= 0),
                        node_name TEXT,
                        creation_timestamp DATETIME,
                        deletion_timestamp DATETIME,
                        labels TEXT DEFAULT '{}',
                        annotations TEXT DEFAULT '{}',
                        container_restarts INTEGER DEFAULT 0 CHECK (container_restarts >= 0),
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')

                # Create events table with constraints
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS pod_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        namespace TEXT NOT NULL,
                        pod_name TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        event_reason TEXT,
                        event_message TEXT,
                        app_name TEXT NOT NULL
                    )
                ''')

                # Create performance-optimized indexes
                indexes = [
                    'CREATE INDEX IF NOT EXISTS idx_pod_name ON pod_history(pod_name)',
                    'CREATE INDEX IF NOT EXISTS idx_timestamp ON pod_history(timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_app_name ON pod_history(app_name)',
                    'CREATE INDEX IF NOT EXISTS idx_pod_type ON pod_history(pod_type)',
                    'CREATE INDEX IF NOT EXISTS idx_ns_ts ON pod_history(namespace, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_ns_pod ON pod_history(namespace, pod_name)',
                    'CREATE INDEX IF NOT EXISTS idx_ns_active ON pod_history(namespace, is_active)',
                    'CREATE INDEX IF NOT EXISTS idx_ns_app_ts ON pod_history(namespace, app_name, timestamp)',
                    'CREATE INDEX IF NOT EXISTS idx_events_pod ON pod_events(namespace, pod_name)',
                    'CREATE INDEX IF NOT EXISTS idx_events_ts ON pod_events(timestamp)'
                ]
                
                for index_sql in indexes:
                    cursor.execute(index_sql)
                
                # Enable query optimization
                cursor.execute('PRAGMA optimize')
                
                logger.info("Database initialized successfully with enhanced schema and indexes")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
            raise DatabaseError(f"Database initialization failed: {str(e)}") from e

    def _to_iso(self, dt):
        """Convert datetime to ISO string format"""
        if dt is None:
            return None
        try:
            return dt.isoformat(sep=' ', timespec='seconds')
        except Exception as e:
            logger.warning(f"Error converting datetime to ISO format: {str(e)}")
            return str(dt)

    @monitor_performance("database")
    def store_pod_data(self, namespace, pod, pod_type, app_name, resources, metrics):
        """Store current pod data with enhanced error handling"""
        try:
            # Validate inputs
            namespace = namespace.strip()
            pod_name = sanitize_pod_name(pod.metadata.name)
            app_name = app_name.strip() if app_name else pod_name
            
            labels_json = json.dumps(dict(pod.metadata.labels or {}))
            annotations_json = json.dumps(dict(pod.metadata.annotations or {}))

            # Count container restarts safely
            restart_count = 0
            if hasattr(pod.status, 'container_statuses') and pod.status.container_statuses:
                restart_count = sum(
                    getattr(cs, 'restart_count', 0) 
                    for cs in pod.status.container_statuses
                )

            creation_ts = self._to_iso(getattr(pod.metadata, 'creation_timestamp', None))

            with self._get_connection() as conn:
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
                    namespace, pod_name, pod_type, app_name, pod.status.phase,
                    float(resources.get('cpu_request', 0)), float(resources.get('cpu_limit', 0)), 
                    float(metrics.get('cpu_usage', 0)),
                    float(resources.get('memory_request', 0)), float(resources.get('memory_limit', 0)), 
                    float(metrics.get('memory_usage', 0)),
                    getattr(pod.spec, 'node_name', None), creation_ts,
                    labels_json, annotations_json, restart_count
                ))
                
                logger.debug(f"Stored pod data for {pod_name} in {namespace}")
                
        except Exception as e:
            logger.error(f"Failed to store pod data for {pod.metadata.name}: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to store pod data: {str(e)}") from e

    @monitor_performance("database")
    def store_pod_data_batch(self, items: List[Tuple]) -> None:
        """Batch insert pod history records with enhanced validation and error handling"""
        if not items:
            logger.debug("No items to store in batch operation")
            return
            
        try:
            def normalize_and_validate(item):
                try:
                    (namespace, pod_name, pod_type, app_name, status,
                     cpu_req, cpu_lim, cpu_use, mem_req, mem_lim, mem_use,
                     node_name, creation_ts, labels, annotations, restarts) = item
                    
                    # Validate and sanitize inputs
                    namespace = namespace.strip() if namespace else ""
                    pod_name = sanitize_pod_name(pod_name)
                    pod_type = pod_type.strip() if pod_type else "unknown"
                    app_name = app_name.strip() if app_name else pod_name
                    
                    # Ensure JSON strings for labels/annotations
                    if not isinstance(labels, str):
                        labels = json.dumps(labels or {})
                    if not isinstance(annotations, str):
                        annotations = json.dumps(annotations or {})
                    
                    # Ensure proper data types
                    cpu_req = float(cpu_req) if cpu_req is not None else 0.0
                    cpu_lim = float(cpu_lim) if cpu_lim is not None else 0.0
                    cpu_use = float(cpu_use) if cpu_use is not None else 0.0
                    mem_req = float(mem_req) if mem_req is not None else 0.0
                    mem_lim = float(mem_lim) if mem_lim is not None else 0.0
                    mem_use = float(mem_use) if mem_use is not None else 0.0
                    restarts = int(restarts) if restarts is not None else 0
                    
                    # Ensure ISO datetime for creation_ts
                    creation_ts = self._to_iso(creation_ts)
                    
                    return (namespace, pod_name, pod_type, app_name, status,
                            cpu_req, cpu_lim, cpu_use, mem_req, mem_lim, mem_use,
                            node_name, creation_ts, labels, annotations, restarts)
                            
                except Exception as e:
                    logger.error(f"Error normalizing batch item: {str(e)}", exc_info=True)
                    raise DatabaseError(f"Failed to normalize batch item: {str(e)}") from e

            normalized_items = [normalize_and_validate(item) for item in items]
            
            # Add current timestamp to each normalized item
            timestamp_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            items_with_timestamp = [
                (timestamp_now,) + item for item in normalized_items
            ]
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT INTO pod_history
                    (timestamp, namespace, pod_name, pod_type, app_name, status,
                     cpu_request, cpu_limit, cpu_usage,
                     memory_request, memory_limit, memory_usage,
                     node_name, creation_timestamp, labels, annotations,
                     container_restarts, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''', items_with_timestamp)
                
                logger.info(f"Successfully stored {len(normalized_items)} pod records in batch operation")
                
        except Exception as e:
            logger.error(f"Batch insert failed: {str(e)}", exc_info=True)
            raise DatabaseError(f"Batch insert operation failed: {str(e)}") from e

    @monitor_performance("database")
    def mark_pods_inactive(self, namespace: str, active_pod_names: List[str]) -> None:
        """Mark pods as inactive if they're no longer running with enhanced error handling"""
        try:
            namespace = namespace.strip()
            active_pod_names = [sanitize_pod_name(name) for name in (active_pod_names or [])]
            
            with self._get_connection() as conn:
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
                
                rows_affected = cursor.rowcount
                if rows_affected > 0:
                    logger.info(f"Marked {rows_affected} pods as inactive in namespace {namespace}")
                    
        except Exception as e:
            logger.error(f"Failed to mark pods inactive: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to mark pods inactive: {str(e)}") from e

    @monitor_performance("database")
    def log_pod_event(self, namespace: str, pod_name: str, event_type: str, 
                     reason: str, message: str, app_name: str) -> None:
        """Log pod lifecycle events with validation"""
        try:
            # Validate and sanitize inputs
            namespace = namespace.strip() if namespace else ""
            pod_name = sanitize_pod_name(pod_name)
            event_type = event_type.strip() if event_type else "unknown"
            app_name = app_name.strip() if app_name else pod_name
            reason = reason.strip() if reason else ""
            message = message[:1000] if message else ""  # Limit message length
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO pod_events
                    (namespace, pod_name, event_type, event_reason, event_message, app_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (namespace, pod_name, event_type, reason, message, app_name))
                
                logger.debug(f"Logged event '{event_type}' for pod {pod_name}")
                
        except Exception as e:
            logger.error(f"Failed to log pod event: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to log pod event: {str(e)}") from e
    @monitor_performance("database")
    def get_historical_data(self, namespace: str, hours_back: int = 48, 
                           app_name: Optional[str] = None) -> pd.DataFrame:
        """Get historical pod data with enhanced error handling"""
        try:
            namespace = namespace.strip()
            
            with self._get_connection() as conn:
                base_query = '''
                    SELECT * FROM pod_history
                    WHERE namespace = ?
                    AND timestamp >= datetime('now', '-{} hours')
                '''.format(int(hours_back))

                params = [namespace]

                if app_name:
                    base_query += ' AND app_name = ?'
                    params.append(app_name.strip())

                base_query += ' ORDER BY timestamp DESC LIMIT 10000'  # Limit for performance

                df = pd.read_sql_query(base_query, conn, params=tuple(params))
                logger.debug(f"Retrieved {len(df)} historical records for {namespace}")
                return df
                
        except Exception as e:
            logger.error(f"Failed to get historical data: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to retrieve historical data: {str(e)}") from e

    @monitor_performance("database")
    def get_pod_timeline(self, namespace: str, pod_name: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Get timeline for a specific pod with validation"""
        try:
            namespace = namespace.strip()
            pod_name = sanitize_pod_name(pod_name)
            
            with self._get_connection() as conn:
                # Get pod data timeline
                pod_df = pd.read_sql_query('''
                    SELECT * FROM pod_history
                    WHERE namespace = ? AND pod_name = ?
                    ORDER BY timestamp
                    LIMIT 5000
                ''', conn, params=(namespace, pod_name))

                # Get pod events timeline
                events_df = pd.read_sql_query('''
                    SELECT * FROM pod_events
                    WHERE namespace = ? AND pod_name = ?
                    ORDER BY timestamp
                    LIMIT 1000
                ''', conn, params=(namespace, pod_name))

                logger.debug(f"Retrieved timeline data: {len(pod_df)} records, {len(events_df)} events")
                return pod_df, events_df
                
        except Exception as e:
            logger.error(f"Failed to get pod timeline: {str(e)}", exc_info=True)
            raise DatabaseError(f"Failed to retrieve pod timeline: {str(e)}") from e

    @monitor_performance("database")
    def cleanup_old_data(self, retention_days: int = HISTORY_RETENTION_DAYS) -> Dict[str, int]:
        """Clean up data older than retention period with enhanced logging"""
        try:
            retention_days = max(1, min(365, int(retention_days)))  # Validate range
            history_deleted = 0
            events_deleted = 0

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Clean up old pod history
                cursor.execute('''
                    DELETE FROM pod_history
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(retention_days))
                history_deleted = cursor.rowcount

                # Clean up old events
                cursor.execute('''
                    DELETE FROM pod_events
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(retention_days))
                events_deleted = cursor.rowcount

                # Commit the deletes
                conn.commit()
                
            # Run VACUUM outside of transaction context
            try:
                # Get a fresh connection for VACUUM operation
                vacuum_conn = self.connection_pool.get_connection()
                if vacuum_conn:
                    vacuum_conn.isolation_level = None  # Enable autocommit mode
                    cursor = vacuum_conn.cursor()
                    cursor.execute('VACUUM')
                    cursor.execute('PRAGMA optimize')
                    self.connection_pool.return_connection(vacuum_conn)
            except Exception as vacuum_error:
                logger.warning(f"Database optimization failed: {str(vacuum_error)}")

            result = {
                'history_records_deleted': history_deleted,
                'events_deleted': events_deleted,
                'retention_days': retention_days
            }

            logger.info(f"Cleanup completed: deleted {history_deleted} history records and {events_deleted} events")
            return result

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}", exc_info=True)
            raise DatabaseError(f"Database cleanup failed: {str(e)}") from e

    @monitor_performance("database")
    def export_historical_data(self, namespace: str, start_date: str, end_date: str, 
                              format: str = 'json') -> str:
        """Export historical data for backup/analysis with validation"""
        try:
            namespace = namespace.strip()
            format = format.lower().strip()
            
            if format not in ['json', 'csv']:
                raise ValueError(f"Unsupported export format: {format}")
            
            # Ensure inclusive end of day by appending time if needed
            start_dt = f"{start_date} 00:00:00" if len(start_date) == 10 else start_date
            end_dt = f"{end_date} 23:59:59" if len(end_date) == 10 else end_date

            with self._get_connection() as conn:
                df = pd.read_sql_query('''
                    SELECT * FROM pod_history
                    WHERE namespace = ?
                    AND timestamp BETWEEN ? AND ?
                    ORDER BY timestamp DESC
                    LIMIT 50000
                ''', conn, params=(namespace, start_dt, end_dt))

                if format == 'json':
                    result = df.to_json(orient='records', date_format='iso')
                elif format == 'csv':
                    result = df.to_csv(index=False)
                else:
                    result = str(df)
                
                logger.info(f"Exported {len(df)} records in {format} format")
                return result
                
        except Exception as e:
            logger.error(f"Export failed: {str(e)}", exc_info=True)
            raise DatabaseError(f"Data export failed: {str(e)}") from e

    @monitor_performance("database")
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics with health information"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Basic counts
                cursor.execute("SELECT COUNT(*) FROM pod_history")
                total_records = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM pod_events")
                total_events = cursor.fetchone()[0]

                cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM pod_history")
                date_range = cursor.fetchone()

                # Database health checks
                cursor.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0]

                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]

                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                
                db_size_mb = (page_count * page_size) / (1024 * 1024)

                # Active pods count
                cursor.execute("SELECT COUNT(*) FROM pod_history WHERE is_active = 1")
                active_pods = cursor.fetchone()[0]

                result = {
                    'total_records': total_records,
                    'total_events': total_events,
                    'active_pods': active_pods,
                    'date_range': date_range,
                    'database_size_mb': round(db_size_mb, 2),
                    'journal_mode': journal_mode,
                    'health_status': 'healthy' if journal_mode == 'wal' else 'warning'
                }
                
                logger.debug(f"Database stats: {total_records} records, {db_size_mb:.1f}MB")
                return result
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {str(e)}", exc_info=True)
            return {
                'total_records': 0,
                'total_events': 0,
                'active_pods': 0,
                'health_status': 'error',
                'error': str(e)
            }

    def list_pod_names(self, namespace: Optional[str] = None) -> List[str]:
        """Return distinct pod names sorted by most recent activity (newest first)."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if namespace:
                    cursor.execute('''
                        SELECT DISTINCT pod_name 
                        FROM pod_history 
                        WHERE namespace = ? 
                        ORDER BY (
                            SELECT MAX(timestamp) 
                            FROM pod_history ph2 
                            WHERE ph2.pod_name = pod_history.pod_name 
                            AND ph2.namespace = pod_history.namespace
                        ) DESC
                    ''', (namespace.strip(),))
                else:
                    cursor.execute('''
                        SELECT DISTINCT pod_name 
                        FROM pod_history 
                        ORDER BY (
                            SELECT MAX(timestamp) 
                            FROM pod_history ph2 
                            WHERE ph2.pod_name = pod_history.pod_name
                        ) DESC
                    ''')
                rows = cursor.fetchall()
                return [r[0] for r in rows]
        except Exception as e:
            logger.error(f"Failed to list pod names: {str(e)}", exc_info=True)
            return []

    def close(self):
        """Close database connections and cleanup"""
        try:
            self.connection_pool.close_all()
            logger.info("Database connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connections: {str(e)}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.close()
        except Exception:
            pass  # Ignore errors during destruction
