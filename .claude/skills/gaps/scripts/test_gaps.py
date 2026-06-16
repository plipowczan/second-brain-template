import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gaps  # noqa: E402

SAMPLE = """# Link Graph

## Outgoing
A -> B, C
B -> A

## Incoming
A <- B
B <- A
C <- A
"""


class TestParse(unittest.TestCase):
    def test_degree_and_weak(self):
        res = gaps.analyze(SAMPLE)
        # A: out 2 + in 1 = 3 ; B: out 1 + in 1 = 2 ; C: out 0 + in 1 = 1 (weak)
        self.assertEqual(res["nodes"], 3)
        self.assertIn("C", res["weakly_connected"])
        self.assertNotIn("A", res["weakly_connected"])
        self.assertNotIn("B", res["weakly_connected"])

    def test_empty_graph(self):
        res = gaps.analyze("# Link Graph\n\n## Outgoing\n\n## Incoming\n")
        self.assertEqual(res["nodes"], 0)
        self.assertEqual(res["weakly_connected"], [])


if __name__ == "__main__":
    unittest.main()
