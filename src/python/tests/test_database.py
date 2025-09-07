"""
Unit tests for database module
"""
import unittest
import tempfile
import os
import sqlite3
from datetime import datetime
from unittest.mock import Mock
from modules.database import HistoryManager


class TestHistoryManager(unittest.TestCase):

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        # Create SQLite configuration for testing
        self.db_config = {
            'type': 'sqlite',
            'path': self.db_path,
            'max_connections': 3,
            'timeout': 30
        }
        self.history_manager = HistoryManager(self.db_config)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_init_database(self):
        """Test database initialization"""
        # Check if tables were created
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check pod_history table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pod_history'")
        self.assertIsNotNone(cursor.fetchone())

        # Check pod_events table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pod_events'")
        self.assertIsNotNone(cursor.fetchone())

        conn.close()

    def _mock_pod(self, name='test-pod'):
        pod = Mock()
        pod.metadata.name = name
        pod.metadata.labels = {'app': 'test'}
        pod.metadata.annotations = {'created-by': 'test'}
        pod.status.phase = 'Running'
        pod.metadata.creation_timestamp = datetime.now()
        pod.spec.node_name = 'node-1'
        pod.status.container_statuses = [Mock(restart_count=0)]
        return pod

    def test_store_pod_data(self):
        """Test storing pod data"""
        pod = self._mock_pod('test-pod')

        resources = {
            'cpu_request': 1.0,
            'cpu_limit': 2.0,
            'memory_request': 1024,
            'memory_limit': 2048
        }

        metrics = {
            'cpu_usage': 0.5,
            'memory_usage': 512
        }

        # Store pod data
        self.history_manager.store_pod_data(
            'test-namespace', pod, 'driver', 'test-app', resources, metrics
        )

        # Verify data was stored
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pod_history WHERE pod_name = 'test-pod'")
        row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[3], 'test-pod')  # pod_name
        self.assertEqual(row[4], 'driver')    # pod_type
        self.assertEqual(row[5], 'test-app')  # app_name

        conn.close()

    def test_store_pod_data_batch(self):
        """Test batch insertion of pod data"""
        pod = self._mock_pod('batch-pod')

        items = [
            (
                'ns', 'batch-pod', 'driver', 'app', 'Running',
                1, 2, 0.5, 1024, 2048, 512,
                'node-1', pod.metadata.creation_timestamp, {'k':'v'}, {'a':'b'}, 0
            )
        ]
        self.history_manager.store_pod_data_batch(items)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pod_history WHERE pod_name='batch-pod'")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)

    def test_mark_pods_inactive(self):
        """Test marking pods as inactive"""
        # First store some active pods
        pod = self._mock_pod('active-pod')

        resources = {'cpu_request': 1, 'cpu_limit': 1, 'memory_request': 1, 'memory_limit': 1}
        metrics = {'cpu_usage': 1, 'memory_usage': 1}

        self.history_manager.store_pod_data('ns', pod, 'driver', 'app', resources, metrics)

        # Mark pods inactive by specifying an unrelated active list
        self.history_manager.mark_pods_inactive('ns', ['another-pod'])

        # Verify pod was marked inactive
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM pod_history WHERE pod_name = 'active-pod'")
        row = cursor.fetchone()

        self.assertEqual(row[0], 0)  # Should be marked inactive

        conn.close()

    def test_get_historical_data(self):
        """Test retrieving historical data"""
        pod = self._mock_pod('hist-pod')
        resources = {'cpu_request': 1, 'cpu_limit': 1, 'memory_request': 1, 'memory_limit': 1}
        metrics = {'cpu_usage': 1, 'memory_usage': 1}

        self.history_manager.store_pod_data('ns', pod, 'driver', 'app', resources, metrics)

        df = self.history_manager.get_historical_data('ns', hours_back=24)

        self.assertFalse(df.empty)
        self.assertEqual(df.iloc[0]['pod_name'], 'hist-pod')

    def test_cleanup_old_data(self):
        """Test cleanup of old data (no-op validation)"""
        self.history_manager.cleanup_old_data(30)

    def test_export_historical_data(self):
        """Test data export functionality"""
        pod = self._mock_pod('export-pod')
        resources = {'cpu_request': 1, 'cpu_limit': 1, 'memory_request': 1, 'memory_limit': 1}
        metrics = {'cpu_usage': 1, 'memory_usage': 1}
        self.history_manager.store_pod_data('ns', pod, 'driver', 'app', resources, metrics)

        # Export data (inclusive end date)
        json_data = self.history_manager.export_historical_data(
            'ns', '2023-01-01', '2025-12-31', 'json'
        )

        self.assertIsInstance(json_data, str)
        self.assertIn('export-pod', json_data)

    def test_get_database_stats(self):
        """Test database statistics retrieval"""
        stats = self.history_manager.get_database_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn('total_records', stats)
        self.assertIn('total_events', stats)
        self.assertIn('date_range', stats)


if __name__ == '__main__':
    unittest.main()
