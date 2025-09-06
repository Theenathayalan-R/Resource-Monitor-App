"""
Performance monitoring utilities
"""
import time
import psutil
import logging
import threading
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from collections import deque
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    db_operations_per_sec: float = 0.0
    k8s_api_calls_per_sec: float = 0.0
    active_connections: int = 0
    response_time_ms: float = 0.0


class PerformanceMonitor:
    """Performance monitoring and metrics collection"""
    
    def __init__(self, max_history: int = 300):  # 5 minutes at 1-second intervals
        self.max_history = max_history
        self.metrics_history = deque(maxlen=max_history)
        self.db_operations = deque(maxlen=100)
        self.api_calls = deque(maxlen=100)
        self.start_time = time.time()
        self._lock = threading.Lock()
        
    def record_system_metrics(self):
        """Record current system performance metrics"""
        try:
            process = psutil.Process()
            
            # Get CPU and memory usage
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            
            # Calculate rates
            now = time.time()
            db_rate = self._calculate_rate(self.db_operations, now)
            api_rate = self._calculate_rate(self.api_calls, now)
            
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_mb=memory_mb,
                db_operations_per_sec=db_rate,
                k8s_api_calls_per_sec=api_rate
            )
            
            with self._lock:
                self.metrics_history.append(metrics)
            
            logger.debug(f"Recorded metrics: CPU={cpu_percent:.1f}%, Memory={memory_mb:.1f}MB")
            
        except Exception as e:
            logger.error(f"Failed to record system metrics: {str(e)}")
    
    def record_db_operation(self):
        """Record a database operation timestamp"""
        with self._lock:
            self.db_operations.append(time.time())
    
    def record_api_call(self):
        """Record a Kubernetes API call timestamp"""
        with self._lock:
            self.api_calls.append(time.time())
    
    def _calculate_rate(self, operations: deque, current_time: float, window_seconds: int = 60) -> float:
        """Calculate operations per second over the specified window"""
        if not operations:
            return 0.0
        
        # Filter operations within the time window
        cutoff_time = current_time - window_seconds
        recent_ops = [op for op in operations if op >= cutoff_time]
        
        return len(recent_ops) / window_seconds if recent_ops else 0.0
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent performance metrics"""
        with self._lock:
            return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of performance metrics"""
        with self._lock:
            if not self.metrics_history:
                return {}
            
            recent_metrics = list(self.metrics_history)[-60:]  # Last minute
            
            cpu_values = [m.cpu_percent for m in recent_metrics]
            memory_values = [m.memory_mb for m in recent_metrics]
            
            return {
                'uptime_seconds': time.time() - self.start_time,
                'current_cpu_percent': recent_metrics[-1].cpu_percent if recent_metrics else 0,
                'current_memory_mb': recent_metrics[-1].memory_mb if recent_metrics else 0,
                'avg_cpu_percent': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'max_cpu_percent': max(cpu_values) if cpu_values else 0,
                'avg_memory_mb': sum(memory_values) / len(memory_values) if memory_values else 0,
                'max_memory_mb': max(memory_values) if memory_values else 0,
                'db_operations_per_sec': recent_metrics[-1].db_operations_per_sec if recent_metrics else 0,
                'k8s_api_calls_per_sec': recent_metrics[-1].k8s_api_calls_per_sec if recent_metrics else 0,
                'total_metrics_recorded': len(self.metrics_history)
            }
    
    def is_performance_degraded(self) -> Dict[str, Any]:
        """Check if performance is degraded based on thresholds"""
        current = self.get_current_metrics()
        if not current:
            return {'degraded': False}
        
        issues = {}
        
        # Check CPU usage
        if current.cpu_percent > 80:
            issues['high_cpu'] = current.cpu_percent
        
        # Check memory usage
        if current.memory_percent > 85:
            issues['high_memory'] = current.memory_percent
        
        # Check response time (if available)
        if current.response_time_ms > 5000:  # 5 seconds
            issues['slow_response'] = current.response_time_ms
        
        return {
            'degraded': bool(issues),
            'issues': issues,
            'timestamp': current.timestamp
        }


# Global performance monitor instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create the global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def monitor_performance(operation_type: str = "general"):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record operation based on type
                if 'database' in operation_type.lower() or 'db' in operation_type.lower():
                    monitor.record_db_operation()
                elif 'kubernetes' in operation_type.lower() or 'k8s' in operation_type.lower():
                    monitor.record_api_call()
                
                # Log performance warnings
                if duration > 5.0:
                    logger.warning(f"{func.__name__} ({operation_type}) took {duration:.2f}s - performance issue detected")
                elif duration > 1.0:
                    logger.info(f"{func.__name__} ({operation_type}) took {duration:.2f}s")
                else:
                    logger.debug(f"{func.__name__} ({operation_type}) took {duration:.3f}s")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{func.__name__} ({operation_type}) failed after {duration:.2f}s: {str(e)}")
                raise
        
        return wrapper
    return decorator


def start_background_monitoring(interval: int = 10):
    """Start background performance monitoring"""
    def monitor_loop():
        monitor = get_performance_monitor()
        while True:
            try:
                monitor.record_system_metrics()
                
                # Check for performance issues
                degradation = monitor.is_performance_degraded()
                if degradation['degraded']:
                    logger.warning(f"Performance degradation detected: {degradation['issues']}")
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Background monitoring error: {str(e)}")
                time.sleep(interval)
    
    # Start monitoring in a daemon thread
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    logger.info(f"Started background performance monitoring with {interval}s interval")


class DatabaseConnectionPool:
    """Simple database connection pool for better performance"""
    
    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self.available_connections = deque()
        self.in_use_connections = set()
        self.lock = threading.Lock()
        self.db_operations_per_second = 0.0
        logger.info(f"Initialized database connection pool with max {max_connections} connections")
    
    def get_connection(self) -> Optional[sqlite3.Connection]:
        """Get a connection from the pool"""
        with self.lock:
            # Clean up closed connections first
            self.available_connections = deque([
                conn for conn in self.available_connections 
                if conn is not None
            ])
            
            if self.available_connections:
                conn = self.available_connections.popleft()
                self.in_use_connections.add(conn)
                self.db_operations_per_second += 0.1  # Small increment for tracking
                logger.debug(f"Reused connection from pool")
                return conn
            
            if len(self.in_use_connections) < self.max_connections:
                # Create thread-safe connection
                conn = sqlite3.connect(
                    self.db_path, 
                    timeout=30.0,
                    check_same_thread=False,  # Allow cross-thread usage
                    isolation_level='DEFERRED'
                )
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('PRAGMA synchronous=NORMAL')
                conn.execute('PRAGMA temp_store=MEMORY')
                conn.execute('PRAGMA cache_size=10000')
                
                self.in_use_connections.add(conn)
                logger.debug(f"Created new connection ({len(self.in_use_connections)}/{self.max_connections})")
                return conn
            
            logger.warning("Connection pool exhausted")
            return None
    
    def return_connection(self, conn):
        """Return a connection to the pool"""
        if conn:
            with self.lock:
                if conn in self.in_use_connections:
                    self.in_use_connections.remove(conn)
                    if len(self.available_connections) < self.max_connections:
                        self.available_connections.append(conn)
                        logger.debug("Returned connection to pool")
                    else:
                        conn.close()
                        logger.debug("Closed excess connection")
    
    def close_all(self):
        """Close all connections in the pool"""
        with self.lock:
            while self.available_connections:
                conn = self.available_connections.popleft()
                try:
                    conn.close()
                except:
                    pass
                    
            for conn in self.in_use_connections.copy():
                try:
                    conn.close()
                except:
                    pass
            self.in_use_connections.clear()
            logger.info("Closed all database connections")
            logger.info("Closed all database connections")
