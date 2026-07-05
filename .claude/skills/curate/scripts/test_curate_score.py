import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import curate_score as cs  # noqa: E402

TODAY = date(2026, 6, 24)


class TestDaysSince(unittest.TestCase):
    def test_parses_iso_date(self):
        self.assertEqual(cs.days_since("2026-06-14", TODAY), 10)

    def test_strips_quotes(self):
        self.assertEqual(cs.days_since('"2026-06-14"', TODAY), 10)

    def test_unparseable_returns_none(self):
        self.assertIsNone(cs.days_since("", TODAY))
        self.assertIsNone(cs.days_since("not-a-date", TODAY))


class TestPoints(unittest.TestCase):
    def test_age_points_brackets(self):
        self.assertEqual(cs.age_points(100), 0)    # <=365
        self.assertEqual(cs.age_points(400), 1)    # <=545
        self.assertEqual(cs.age_points(600), 2)    # <=730
        self.assertEqual(cs.age_points(900), 3)    # >730
        self.assertEqual(cs.age_points(None), 0)   # unknown age contributes nothing

    def test_isolation_points(self):
        self.assertEqual(cs.isolation_points(0, 0), 2)
        self.assertEqual(cs.isolation_points(1, 0), 1)
        self.assertEqual(cs.isolation_points(0, 1), 1)
        self.assertEqual(cs.isolation_points(3, 2), 0)


class TestScoreNote(unittest.TestCase):
    def test_fresh_linked_alive_scores_zero(self):
        score, reasons = cs.score_note(100, 3, 2, False)
        self.assertEqual(score, 0)
        self.assertEqual(reasons, [])

    def test_dead_link_dominates(self):
        score, reasons = cs.score_note(100, 3, 2, True)
        self.assertEqual(score, 4)
        self.assertIn("dead source/repo link", reasons)

    def test_old_orphan_accumulates(self):
        score, reasons = cs.score_note(900, 0, 0, False)
        self.assertEqual(score, 5)  # 3 age + 2 isolation
        self.assertEqual(len(reasons), 2)


class TestRecommendAction(unittest.TestCase):
    def test_dead_link_archives(self):
        self.assertEqual(cs.recommend_action(4, True, False), "archive")

    def test_superseder_merges(self):
        self.assertEqual(cs.recommend_action(2, False, True), "merge")

    def test_high_score_archives(self):
        self.assertEqual(cs.recommend_action(4, False, False), "archive")

    def test_mid_score_refreshes(self):
        self.assertEqual(cs.recommend_action(2, False, False), "refresh")
        self.assertEqual(cs.recommend_action(3, False, False), "refresh")

    def test_low_score_keeps(self):
        self.assertEqual(cs.recommend_action(1, False, False), "keep")


class TestParseGraph(unittest.TestCase):
    def test_counts_edges(self):
        text = (
            "## Outgoing\n"
            "AI/Foo -> BAR, BAZ\n"
            "AI/Lonely -> -\n"
            "## Incoming\n"
            "BAR <- AI/Foo\n"
            "BAZ <- AI/Foo\n"
        )
        g = cs.parse_graph(text)
        self.assertEqual(g["AI/Foo"], (0, 2))   # 2 outgoing, 0 incoming
        self.assertEqual(g["BAR"], (1, 0))       # 1 incoming, 0 outgoing
        self.assertEqual(g["AI/Lonely"], (0, 0)) # "-> -" means no edges


if __name__ == "__main__":
    unittest.main()
