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


class TestUnderscoreFiles(unittest.TestCase):
    def test_scan_skips_underscore_prefixed_files(self):
        with tempfile.TemporaryDirectory() as d:
            content = Path(d) / "content"
            (content / "T").mkdir(parents=True)
            (content / "_privacy.md").write_text("# Privacy rules\n", encoding="utf-8")
            (content / "T" / "_draft.md").write_text("# Draft\n", encoding="utf-8")
            (content / "T" / "Loose.md").write_text("# Loose\n", encoding="utf-8")
            res = lint_scan.scan(str(content))
            self.assertEqual(res["total"], 1)
            self.assertEqual(res["issues"]["missing_frontmatter"],
                             [str(content / "T" / "Loose.md").replace("\\", "/")])


class TestBlockStyleFrontmatter(unittest.TestCase):
    def test_parse_fm_collects_block_list(self):
        fm, _ = lint_scan.parse_fm(
            '---\ntitle: "X"\ntags:\n  - book\n  - learning\ntype: book-note\n---\nbody\n')
        self.assertEqual(fm["tags"], ["book", "learning"])
        self.assertEqual(fm["title"], '"X"')

    def test_scan_does_not_flag_block_style_tags(self):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "content" / "T"
            c.mkdir(parents=True)
            (c / "Block.md").write_text(
                '---\ntitle: "Block"\ndate: 2026-01-01\ntype: book-note\n'
                'tags:\n  - book\n  - learning\nsummary: "s"\n---\n# Block\n' + ("x " * 200),
                encoding="utf-8")
            res = lint_scan.scan(str(Path(d) / "content"))
            self.assertEqual(res["issues"]["missing_tags"], [])


def note(fm_lines, body="x " * 150):
    return "---\n" + "\n".join(fm_lines) + "\n---\n# N\n" + body


# Today's date, so the note never turns stale and the no-findings test keeps holding.
VALID_FM = ['title: "N"', f"date: {lint_scan.TODAY.isoformat()}", "type: knowledge-note",
            'tags: ["a"]', 'summary: "s"']


class TestSourceValues(unittest.TestCase):
    def values(self, text):
        fm, _ = lint_scan.parse_fm(text)
        return lint_scan.source_values(fm)

    def test_scalar(self):
        self.assertEqual(self.values('---\nsource: "_raw/inbox/a.md"\n---\n'),
                         ["_raw/inbox/a.md"])

    def test_block_list(self):
        self.assertEqual(
            self.values('---\nsources:\n  - "_raw/processed/a.md"\n  - https://x.io/p\n---\n'),
            ["_raw/processed/a.md", "https://x.io/p"])

    def test_flow_list_with_comma_inside_quotes(self):
        self.assertEqual(
            self.values("---\nsources: [\"_raw/processed/a.md\", 'Call, with vendor']\n---\n"),
            ["_raw/processed/a.md", "Call, with vendor"])

    def test_both_fields(self):
        self.assertEqual(
            self.values("---\nsource: _raw/a.md\nsources: [_raw/b.md]\n---\n"),
            ["_raw/a.md", "_raw/b.md"])

    def test_trailing_comments_are_removed(self):
        # The AGENTS.template.md frontmatter example writes a commented flow list.
        self.assertEqual(
            self.values('---\nsources: ["_raw/processed/a.md"]  # or source: "<one>"\n---\n'),
            ["_raw/processed/a.md"])
        self.assertEqual(self.values('---\nsource: "_raw/inbox/a.md" # moved\n---\n'),
                         ["_raw/inbox/a.md"])
        self.assertEqual(self.values("---\nsource: _raw/inbox/a.md # moved\n---\n"),
                         ["_raw/inbox/a.md"])
        self.assertEqual(
            self.values('---\nsources:  # list\n  - "_raw/a.md"  # first\n  - _raw/b.md\n---\n'),
            ["_raw/a.md", "_raw/b.md"])
        self.assertEqual(self.values("---\nsource: # none yet\n---\n"), [])

    def test_hash_that_is_not_a_comment_is_kept(self):
        self.assertEqual(
            self.values("---\nsources: [\"_raw/a #1.md\", https://x.io/p#frag, 'Q&A #2']\n---\n"),
            ["_raw/a #1.md", "https://x.io/p#frag", "Q&A #2"])

    def test_apostrophe_inside_plain_scalar(self):
        self.assertEqual(
            self.values("---\nsources: [Bob's call, _raw/a.md]  # two\n---\n"),
            ["Bob's call", "_raw/a.md"])
        self.assertEqual(self.values("---\nsource: 'Bob''s call'\n---\n"), ["Bob's call"])


class TestMissingSourceFile(unittest.TestCase):
    def scan(self, fm_extra, processed=(), existing=()):
        with tempfile.TemporaryDirectory() as d:
            content = Path(d) / "content"
            (content / "T").mkdir(parents=True)
            (content / "_raw" / "processed").mkdir(parents=True)
            (content / "_raw" / "inbox").mkdir(parents=True)
            for name in processed:
                (content / "_raw" / "processed" / name).write_text("src", encoding="utf-8")
            for rel in existing:
                (content / rel).write_text("src", encoding="utf-8")
            (content / "T" / "N.md").write_text(note(VALID_FM + fm_extra), encoding="utf-8")
            return lint_scan.scan(str(content))

    def test_one_archived_copy_gives_fix(self):
        res = self.scan(['source: "_raw/inbox/talk.md"'], processed=["2026-07-02_talk.md"])
        self.assertEqual(len(res["issues"]["missing_source_file"]), 1)
        self.assertIn("source=_raw/inbox/talk.md, fix=_raw/processed/2026-07-02_talk.md",
                      res["issues"]["missing_source_file"][0])

    def test_two_archived_copies_give_candidates_only(self):
        res = self.scan(['source: "_raw/inbox/talk.md"'],
                        processed=["2026-07-02_talk.md", "2026-08-10_talk.md"])
        [finding] = res["issues"]["missing_source_file"]
        self.assertIn("candidates=_raw/processed/2026-07-02_talk.md|"
                      "_raw/processed/2026-08-10_talk.md", finding)
        self.assertNotIn("fix=", finding)

    def test_no_copy_plain_finding(self):
        res = self.scan(['source: "_raw/inbox/talk.md"'], processed=["2026-07-02_other.md"])
        [finding] = res["issues"]["missing_source_file"]
        self.assertTrue(finding.endswith("(source=_raw/inbox/talk.md)"))

    def test_existing_path_no_finding(self):
        res = self.scan(['source: "_raw/processed/2026-07-02_talk.md"'],
                        processed=["2026-07-02_talk.md"])
        self.assertEqual(res["issues"]["missing_source_file"], [])

    def test_content_prefix_resolved_and_kept_in_fix(self):
        res = self.scan(['sources: ["content/_raw/inbox/talk.md"]'],
                        processed=["2026-07-02_talk.md"])
        [finding] = res["issues"]["missing_source_file"]
        self.assertIn("fix=content/_raw/processed/2026-07-02_talk.md", finding)
        res = self.scan(['source: "content/_raw/processed/2026-07-02_talk.md"'],
                        processed=["2026-07-02_talk.md"])
        self.assertEqual(res["issues"]["missing_source_file"], [])

    def test_missing_youtube_archive_plain_finding(self):
        res = self.scan(['source: "_raw/processed/2026-05-22_yt-abc_talk.md"'])
        [finding] = res["issues"]["missing_source_file"]
        self.assertTrue(finding.endswith("(source=_raw/processed/2026-05-22_yt-abc_talk.md)"))

    def test_urls_wikilinks_and_text_are_skipped(self):
        res = self.scan(['sources:', '  - "https://example.com/post"', '  - "[[Other Note]]"',
                         '  - "Call with the vendor"'])
        self.assertEqual(res["issues"]["missing_source_file"], [])

    def test_commented_source_fields_are_checked(self):
        res = self.scan(['sources: ["_raw/processed/missing.md"]  # source archive',
                         'source: "_raw/inbox/talk.md" # moved'],
                        processed=["2026-07-02_talk.md"])
        details = [f.split(" (", 1)[1] for f in res["issues"]["missing_source_file"]]
        self.assertEqual(sorted(details), [
            "source=_raw/inbox/talk.md, fix=_raw/processed/2026-07-02_talk.md)",
            "source=_raw/processed/missing.md)"])

    def test_one_finding_per_missing_path(self):
        res = self.scan(['sources: ["_raw/inbox/a.md", "_raw/inbox/b.md", "_raw/inbox/ok.md"]'],
                        existing=["_raw/inbox/ok.md"])
        self.assertEqual(len(res["issues"]["missing_source_file"]), 2)


class TestContradiction(unittest.TestCase):
    def scan(self, body):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / "content" / "T"
            c.mkdir(parents=True)
            (c / "N.md").write_text(note(VALID_FM, body + "x " * 150), encoding="utf-8")
            return lint_scan.scan(str(Path(d) / "content"))

    def test_two_markers(self):
        res = self.scan("> [!contradiction] Price\n> Earlier: 10\n> New: 20\n\n"
                        "> [!contradiction]\n> Earlier: a\n> New: b\n")
        [finding] = res["issues"]["contradiction"]
        self.assertTrue(finding.endswith("(2 markers)"))

    def test_case_insensitive(self):
        res = self.scan("> [!CONTRADICTION] Date\n> Earlier: 2025\n> New: 2026\n")
        [finding] = res["issues"]["contradiction"]
        self.assertTrue(finding.endswith("(1 marker)"))

    def test_marker_in_code_block_ignored(self):
        res = self.scan("Format:\n\n```markdown\n> [!contradiction] Title\n> Earlier: a\n```\n")
        self.assertEqual(res["issues"]["contradiction"], [])

    def test_note_without_marker(self):
        res = self.scan("> [!note] Just a note\n")
        self.assertEqual(res["issues"]["contradiction"], [])


class TestWarningsAndCompatibility(unittest.TestCase):
    def test_output_keys_and_warnings(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "content").mkdir()
            res = lint_scan.scan(str(Path(d) / "content"))
        self.assertEqual(set(res), {"total", "issues", "counts", "warnings"})
        self.assertEqual(res["warnings"], ["missing_source_file", "contradiction"])
        for key in ("missing_frontmatter", "missing_title", "missing_date", "missing_tags",
                    "missing_type", "missing_summary", "bad_type", "stub", "todo", "stale",
                    "title_filename_mismatch", "schema_violation"):
            self.assertIn(key, res["issues"])
            self.assertIn(key, res["counts"])

    def test_note_valid_under_0_2_1_has_no_findings(self):
        schema = {"knowledge-note": {"required": ["title", "date", "type", "tags", "summary"]}}
        with tempfile.TemporaryDirectory() as d:
            content = Path(d) / "content"
            (content / "T").mkdir(parents=True)
            (content / "_raw" / "processed").mkdir(parents=True)
            (content / "_raw" / "processed" / "2026-01-01_src.md").write_text(
                "src", encoding="utf-8")
            (content / "T" / "N.md").write_text(
                note(VALID_FM + ['source: "_raw/processed/2026-01-01_src.md"']),
                encoding="utf-8")
            res = lint_scan.scan(str(content), schema)
        self.assertEqual({k: v for k, v in res["counts"].items() if v}, {})


if __name__ == "__main__":
    unittest.main()
