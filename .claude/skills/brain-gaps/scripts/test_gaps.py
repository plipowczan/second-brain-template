import contextlib
import io
import json
import sys
import tempfile
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


def answer(title, day, gaps=None):
    field = "" if gaps is None else f"gaps: {gaps}\n"
    return (f'---\ntitle: "{title}"\ndate: {day}\ntype: answer-note\nsummary: "s"\n{field}'
            f"---\n# {title}\nBody.\n")


class TestAnswerGaps(unittest.TestCase):
    def test_lists_only_answers_with_open_gaps(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.md").write_text(answer("Pricing", "2026-10-01", 2), encoding="utf-8")
            (Path(d) / "b.md").write_text(answer("Setup", "2026-10-02", 0), encoding="utf-8")
            (Path(d) / "c.md").write_text(answer("Old", "2026-01-01"), encoding="utf-8")
            res = gaps.answer_gaps(d)
        self.assertEqual([(a["title"], a["date"], a["gaps"]) for a in res],
                         [("Pricing", "2026-10-01", 2)])
        self.assertTrue(res[0]["path"].endswith("/a.md"))

    def test_newest_first(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x.md").write_text(answer("Older", "2026-09-01", 1), encoding="utf-8")
            (Path(d) / "y.md").write_text(answer("Newer", "2026-10-05", 3), encoding="utf-8")
            res = gaps.answer_gaps(d)
        self.assertEqual([a["title"] for a in res], ["Newer", "Older"])

    def test_missing_folder(self):
        self.assertEqual(gaps.answer_gaps("definitely-not-a-folder"), [])

    def test_main_keeps_existing_keys(self):
        with tempfile.TemporaryDirectory() as d:
            graph = Path(d) / "graph.md"
            graph.write_text(SAMPLE, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = gaps.main(["--graph", str(graph), "--answers", str(Path(d) / "none")])
        res = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(set(res), {"nodes", "weak_count", "weakly_connected", "answer_gaps"})
        self.assertEqual(res["answer_gaps"], [])


if __name__ == "__main__":
    unittest.main()
