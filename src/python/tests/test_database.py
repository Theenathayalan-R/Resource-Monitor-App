"""
Unit tests for database module
"""
import unittest
import tempfile
import os
import sqlite3
from datetime import datetime
from unittest.mock import Mock, patch
from modules.database import HistoryManager


class TestHistoryManager(unittest.TestCase):

    def setUp(self):
        """Set up test database"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.history_manager = HistoryManager(self.db_path)

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

    def test_store_pod_data(self):
        """Test storing pod data"""
        # Create mock pod
        pod = Mock()
        pod.metadata.name = 'test-pod'
        pod.metadata.labels = {'app': 'test'}
        pod.metadata.annotations = {'created-by': 'test'}
        pod.status.phase = 'Running'
        pod.metadata.creation_timestamp = datetime.now()
        pod.spec.node_name = 'node-1'
        pod.status.container_statuses = [Mock(restart_count=0)]

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

    def test_mark_pods_inactive(self):
        """Test marking pods as inactive"""
        # First store some active pods
        pod = Mock()
        pod.metadata.name = 'active-pod'
        pod.metadata.labels = {}
        pod.metadata.annotations = {}
        pod.status.container_statuses = []
        pod.metadata.creation_timestamp = datetime.now()
        pod.spec.node_name = 'node-1'
        pod.status.phase = 'Running'

        resources = {'cpu_request': 1, 'cpu_limit': 1, 'memory_request': 1, 'memory_limit': 1}
        metrics = {'cpu_usage': 1, 'memory_usage': 1}

        self.history_manager.store_pod_data('ns', pod, 'driver', 'app', resources, metrics)

        # Mark pods inactive
        self.history_manager.mark_pods_inactive('ns', ['inactive-pod'])

        # Verify pod was marked inactive
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM pod_history WHERE pod_name = 'active-pod'")
        row = cursor.fetchone()

        self.assertEqual(row[0], 0)  # Should be marked inactive

        conn.close()

    def test_get_historical_data(self):
        """Test retrieving historical data"""
        # Store test data
        pod = Mock()
        pod.metadata.name = 'test-pod'
        pod.metadata.labels = {}
        pod.metadata.annotations = {}
        pod.status.container_statuses = []
        pod.metadata.creation_timestamp = datetime.now()
        pod.spec.node_name = 'node-1'
        pod.status.phase = 'Running'

        resources = {'cpu_request': 1, 'cpu_limit': 1, 'memory_request': 1, 'memory_limit': 1}
        metrics = {'cpu_usage': 1, 'memory_usage': 1}

        self.history_manager.store_pod_data('ns', pod, 'driver', 'app', resources, metrics)

        # Retrieve data
        df = self.history_manager.get_historical_data('ns', hours_back=24)

        self.assertFalse(df.empty)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['pod_name'], 'test-pod')

    def test_cleanup_old_data(self):
        """Test cleanup of old data"""
        # This test would require manipulating timestamps
        # For now, just ensure the method runs without error
        self.history_manager.cleanup_old_data(30)
        # If we get here without exception, the test passes

    def test_export_historical_data(self):
        """Test data export functionality"""
        # Store test data
        pod = Mock()
        pod.metadata.name = 'export-pod'
        pod.metadata.labels = {}
        pod.metadata.annotations = {}
        pod.status.container_statuses = []
        pod.metadata.creation_timestamp = datetime.now()
        pod.spec.node_name = 'node-1'
        pod.status.phase = 'Running'

        resources = {'cpu_request': 1, 'cpu_limit': 1, 'memory_request': 1, 'memory_limit': 1}
        metrics = {'cpu_usage': 1, 'memory_usage': 1}

        self.history_manager.store_pod_data('ns', pod, 'driver', 'app', resources, metrics)

        # Export data
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
