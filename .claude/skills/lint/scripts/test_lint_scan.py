import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lint_scan  # noqa: E402


class TestSchemaFunctions(unittest.TestCase):
    def test_no_violation_when_complete(self):
        schema = {"knowledge-note": {"required": ["title", "date", "type", "tags", "summary"]}}
        fm = {"title": "X", "date": "2026-01-01", "type": "knowledge-note",
              "tags": '["a"]', "summary": "s"}
        self.assertEqual(lint_scan.schema_violations(fm, "knowledge-note", schema), [])

    def test_reports_missing(self):
        schema = {"tool": {"required": ["title", "summary"]}}
        self.assertEqual(lint_scan.schema_violations({"title": "X"}, "tool", schema), ["summary"])

    def test_unknown_type_no_violation(self):
        self.assertEqual(lint_scan.schema_violations({}, "mystery", {"tool": {"required": ["x"]}}), [])

    def test_load_schema_missing_file(self):
        self.assertEqual(lint_scan.load_schema("definitely-not-here.yml"), {})


class TestScanIntegration(unittest.TestCase):
    def test_scan_flags_schema_violation(self):
        schema = {"knowledge-note": {"required": ["title", "date", "type", "tags", "summary"]}}
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "content" / "T"
            c.mkdir(parents=True)
            (c / "Bad.md").write_text(
                '---\ntitle: "Bad"\ndate: 2026-01-01\ntype: knowledge-note\n---\n# Bad\n'
                + ("x" * 300), encoding="utf-8")
            res = lint_scan.scan(str(Path(d) / "content"), schema)
            self.assertTrue(any("missing=" in s for s in res["issues"]["schema_violation"]))

    def test_scan_clean_when_complete(self):
        schema = {"knowledge-note": {"required": ["title", "date", "type", "tags", "summary"]}}
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "content" / "T"
            c.mkdir(parents=True)
            (c / "Good.md").write_text(
                '---\ntitle: "Good"\ndate: 2026-01-01\ntype: knowledge-note\n'
                'tags: ["a"]\nsummary: "s"\n---\n# Good\n' + ("x " * 200), encoding="utf-8")
            res = lint_scan.scan(str(Path(d) / "content"), schema)
            self.assertEqual(res["issues"]["schema_violation"], [])
            self.assertEqual(res["issues"]["bad_type"], [])


if __name__ == "__main__":
    unittest.main()
