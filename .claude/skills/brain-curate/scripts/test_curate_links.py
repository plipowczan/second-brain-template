import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import curate_links as cl  # noqa: E402


class TestClassifyStatus(unittest.TestCase):
    def test_2xx_3xx_alive(self):
        self.assertEqual(cl.classify_status(200), "alive")
        self.assertEqual(cl.classify_status(301), "alive")
        self.assertEqual(cl.classify_status(399), "alive")

    def test_404_410_dead(self):
        self.assertEqual(cl.classify_status(404), "dead")
        self.assertEqual(cl.classify_status(410), "dead")

    def test_blocked_codes_unverified(self):
        # 401/403/429 are access blocks, not proof the resource is gone
        self.assertEqual(cl.classify_status(401), "unverified")
        self.assertEqual(cl.classify_status(403), "unverified")
        self.assertEqual(cl.classify_status(429), "unverified")

    def test_5xx_unverified(self):
        self.assertEqual(cl.classify_status(500), "unverified")
        self.assertEqual(cl.classify_status(503), "unverified")

    def test_network_error_unverified(self):
        # a timeout / DNS failure is never proof of death
        self.assertEqual(cl.classify_status(None, network_error=True), "unverified")

    def test_none_without_error_unverified(self):
        self.assertEqual(cl.classify_status(None), "unverified")


if __name__ == "__main__":
    unittest.main()
