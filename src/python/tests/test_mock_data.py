"""
Unit tests for mock data generators
"""
import unittest
from modules.mock_data import generate_mock_pods, generate_mock_metrics
from modules.utils import get_pod_resources, classify_spark_pods


class TestMockData(unittest.TestCase):
    def test_generate_mock_pods_structure(self):
        pods, drivers, executors = generate_mock_pods("ns", drivers=2, executors_per_driver=3)
        # counts
        self.assertEqual(len(drivers), 2)
        self.assertEqual(len(executors), 2 * 3)
        self.assertEqual(len(pods), len(drivers) + len(executors))
        # naming conventions
        self.assertTrue(all("-driver" in d.metadata.name for d in drivers))
        self.assertTrue(all("-exec-" in e.metadata.name for e in executors))
        # classification consistency
        c_drivers, c_executors = classify_spark_pods(pods)
        self.assertEqual({d.metadata.name for d in drivers}, {d.metadata.name for d in c_drivers})
        self.assertEqual({e.metadata.name for e in executors}, {e.metadata.name for e in c_executors})

    def test_generate_mock_metrics_ranges(self):
        pods, drivers, executors = generate_mock_pods("ns", drivers=1, executors_per_driver=2)
        metrics = generate_mock_metrics(pods)
        self.assertEqual(set(metrics.keys()), {p.metadata.name for p in pods})
        for m in metrics.values():
            # CPU cores in [0.1, 0.9]
            self.assertGreaterEqual(m["cpu_usage"], 0.1)
            self.assertLessEqual(m["cpu_usage"], 0.9)
            # Memory MiB in [256, 2048]
            self.assertGreaterEqual(m["memory_usage"], 256)
            self.assertLessEqual(m["memory_usage"], 2048)

    def test_get_pod_resources_from_mock(self):
        pods, drivers, executors = generate_mock_pods("ns", drivers=1, executors_per_driver=1)
        any_pod = pods[0]
        res = get_pod_resources(any_pod)
        # Defaults in mock are cpu_req=500m(0.5 cores), cpu_lim=1 core, mem_req=1024Mi, mem_lim=2048Mi
        self.assertAlmostEqual(res['cpu_request'], 0.5, places=3)
        self.assertAlmostEqual(res['cpu_limit'], 1.0, places=3)
        self.assertEqual(res['memory_request'], 1024)
        self.assertEqual(res['memory_limit'], 2048)


if __name__ == '__main__':
    unittest.main()
