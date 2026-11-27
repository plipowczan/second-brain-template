#!/usr/bin/env python3
"""Tests for oplog.py — run from this folder: python -m unittest test_oplog"""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "oplog.py"

sys.path.insert(0, str(HERE))
import oplog  # noqa: E402

HEADER = (b"# Operation log\n\n| When (UTC) | Operation | What | Notes |\n"
          b"|---|---|---|---|\n")
# A base whose owner deleted brain-export has no masking to test (oplog then writes
# unmasked rows; test_privacy_script_missing covers that case everywhere).
HAS_PRIVACY = (oplog.PRIVACY_DIR / oplog.PRIVACY_SCRIPT).is_file()
needs_privacy = unittest.skipUnless(HAS_PRIVACY, "brain-export/scripts/privacy_sweep.py is not installed")
PRIVACY_LOCAL = "## Always cut\n\n- \"Acme Labs\" — client\n"


def run(cwd, *args, root=None):
    """Run oplog.py as the skills do; returns (exit code, stdout, stderr) as text."""
    cmd = [sys.executable, str(SCRIPT)] + (["--root", str(root)] if root else []) + list(args)
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True)
    return p.returncode, p.stdout.decode("utf-8"), p.stderr.decode("utf-8")


def run_here(root, *args):
    """oplog.main in this process (faster); returns (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = oplog.main(["--root", str(root)] + list(args))
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class VaultCase(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        (self.root / "content").mkdir()
        self.log = self.root / "content" / "_outputs" / "log.md"

    def tearDown(self):
        self._td.cleanup()

    def append(self, *args, at="2026-11-27T14:03"):
        extra = ["--at", at] if at else []
        return run(self.root, "append", *args, *extra)

    def read(self, *args):
        code, out, err = run(self.root, "read", *args)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def privacy(self, text=PRIVACY_LOCAL):
        (self.root / "content" / "_privacy.local.md").write_text(text, encoding="utf-8")


class TestAppend(VaultCase):
    def test_creates_file_with_header(self):
        # As a skill calls it: from the vault root, no --root.
        code, out, err = self.append("--op", "ingest", "--count", "sources=3", "--count", "created=2",
                                     "--count", "updated=5", "--note", "AI/Agents.md",
                                     "--note", "AI/Tools/Foo.md")
        self.assertEqual(code, 0, err)
        row = b"| 2026-11-27 14:03 | ingest | sources=3 created=2 updated=5 | `AI/Agents.md`, `AI/Tools/Foo.md` |\n"
        self.assertEqual(self.log.read_bytes(), HEADER + row)
        self.assertEqual(out.rstrip("\r\n"), row.decode("utf-8").rstrip("\n"))  # printed too
        self.assertEqual(err, "" if HAS_PRIVACY else oplog.NOTICE + "\n")

    def test_header_is_the_documented_one(self):
        self.assertEqual(oplog.HEADER.encode("utf-8"), HEADER)

    def test_root_before_or_after_the_command(self):
        elsewhere = self.root / "content"  # any folder that is not the vault root
        code, _, err = run(elsewhere, "append", "--op", "enhance", "--at", "2026-11-27T10:00",
                           root=self.root)
        self.assertEqual(code, 0, err)
        code, _, err = run(elsewhere, "append", "--root", str(self.root), "--op", "compile",
                           "--at", "2026-11-27T11:00")
        self.assertEqual(code, 0, err)
        self.assertEqual([r["op"] for r in self.read()], ["enhance", "compile"])

    def test_appends_to_existing_file(self):
        self.append("--op", "ingest", "--note", "A.md")
        before = self.log.read_bytes()
        code, _, err = self.append("--op", "enhance", "--count", "updated=1", "--note", "B.md",
                                   at="2026-11-28T09:00")
        self.assertEqual(code, 0, err)
        after = self.log.read_bytes()
        self.assertEqual(after[:len(before)], before)
        self.assertEqual(after[len(before):],
                         b"| 2026-11-28 09:00 | enhance | updated=1 | `B.md` |\n")
        self.assertEqual(after.count(b"# Operation log"), 1)

    def test_adds_missing_final_newline(self):
        self.log.parent.mkdir()
        before = HEADER + b"Owner's own line, no newline at the end"
        self.log.write_bytes(before)
        code, _, err = self.append("--op", "curate", "--count", "retired=2")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.log.read_bytes(),
                         before + b"\n| 2026-11-27 14:03 | curate | retired=2 | - |\n")

    def test_hand_written_lines_kept_byte_for_byte(self):
        self.log.parent.mkdir()
        before = (HEADER
                  + b"| 2026-11-01 08:00 | ingest | sources=1 | `A.md` |\n"
                  + "Ręcznie: przeniosłem dwie notatki | sam\r\n".encode("utf-8")
                  + b"\n"
                  + b"| not | a | row |\n")
        self.log.write_bytes(before)
        code, _, err = self.append("--op", "refactor", "--count", "moved=1", "--note", "B.md")
        self.assertEqual(code, 0, err)
        after = self.log.read_bytes()
        self.assertEqual(after[:len(before)], before)
        self.assertEqual(after[len(before):],
                         b"| 2026-11-27 14:03 | refactor | moved=1 | `B.md` |\n")
        self.assertEqual([r["op"] for r in self.read()], ["ingest", "refactor"])

    def test_empty_existing_file_gets_the_header(self):
        self.log.parent.mkdir()
        self.log.write_bytes(b"")
        code, _, err = self.append("--op", "watch")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.log.read_bytes(), HEADER + b"| 2026-11-27 14:03 | watch | - | - |\n")

    def test_no_counts_no_notes(self):
        self.append("--op", "review")
        self.assertTrue(self.log.read_bytes().endswith(b"| 2026-11-27 14:03 | review | - | - |\n"))
        self.assertEqual(self.read(), [{"time": "2026-11-27 14:03", "op": "review",
                                        "counts": {}, "notes": [], "more": 0}])

    def test_refused_input_writes_nothing(self):
        bad = [
            ["--op", "ingest", "--count", "summary=great"],
            ["--op", "ingest", "--count", "n=-1"],
            ["--op", "ingest", "--count", "n=1.5"],
            ["--op", "ingest", "--count", "Created=1"],
            ["--op", "ingest", "--count", "created"],
            ["--op", "ingest", "--count", "created=1 updated=2"],
            ["--op", "Ingest"],
            ["--op", "ingest now"],
            ["--op", "9ingest"],
            ["--op", "-"],
            ["--op", "ingest", "--note", "AI/`Agents`.md"],
            ["--op", "ingest", "--note", "AI/Agents\n.md"],
            ["--op", "ingest", "--note", "AI/Agents\r.md"],
            ["--op", "ingest", "--note", ""],
            ["--op", "ingest", "--note", "A\udcff.md"],   # an undecodable byte in argv
            ["--op", "ingest", "--at", "2026-11-27 14:03"],
            ["--op", "ingest", "--at", "2026-13-27T14:03"],
            ["--count", "created=1"],
        ]
        # The exit code as a calling skill sees it.
        code, out, err = run(self.root, "append", "--op", "ingest", "--count", "summary=great")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("summary=great", err)
        for args in bad:
            with self.subTest(args=args):
                code, out, err = run_here(self.root, "append", *args)
                self.assertEqual(code, 2, err)
                self.assertEqual(out, "")
                self.assertIn("error", err)
                self.assertFalse((self.root / "content" / "_outputs").exists())
        # And with a log already there, its bytes stay as they are.
        self.append("--op", "ingest", "--note", "A.md")
        before = self.log.read_bytes()
        for args in bad:
            with self.subTest(existing=args):
                code, _, _ = run_here(self.root, "append", *args)
                self.assertEqual(code, 2)
                self.assertEqual(self.log.read_bytes(), before)

    def test_no_content_folder(self):
        (self.root / "content").rmdir()
        code, _, err = self.append("--op", "ingest")
        self.assertEqual(code, 1)
        self.assertIn("no content/", err)
        self.assertFalse((self.root / "content").exists())

    def test_fourteen_notes(self):
        args = ["--op", "ingest"]
        for i in range(14):
            args += ["--note", f"N/{i:02d}.md"]
        code, _, err = self.append(*args)
        self.assertEqual(code, 0, err)
        last = self.log.read_text(encoding="utf-8").splitlines()[-1]
        self.assertTrue(last.endswith(" | `N/00.md`, `N/01.md`, `N/02.md`, `N/03.md`, `N/04.md`, "
                                      "`N/05.md`, `N/06.md`, `N/07.md`, `N/08.md`, `N/09.md` "
                                      "and 4 more |"), last)
        (row,) = self.read()
        self.assertEqual(row["notes"], [f"N/{i:02d}.md" for i in range(10)])
        self.assertEqual(row["more"], 4)

    def test_repeated_note_listed_once(self):
        self.append("--op", "ingest", "--note", "A.md", "--note", "B.md", "--note", "A.md",
                    "--note", "B.md")
        self.assertEqual(self.read()[0]["notes"], ["A.md", "B.md"])

    def test_pipe_escaped_and_read_back(self):
        code, _, err = self.append("--op", "ingest", "--note", "AI/a|b.md", "--note", "c.md")
        self.assertEqual(code, 0, err)
        self.assertIn(b"`AI/a\\|b.md`, `c.md`", self.log.read_bytes())
        self.assertEqual(self.read()[0]["notes"], ["AI/a|b.md", "c.md"])

    def test_windows_backslash_paths(self):
        self.append("--op", "refactor", "--note", "AI\\Agents\\Foo.md", "--note", "_raw\\processed\\x.md")
        self.assertEqual(self.read()[0]["notes"], ["AI/Agents/Foo.md", "_raw/processed/x.md"])
        self.assertNotIn(b"\\", self.log.read_bytes().split(b"\n")[-2])

    def test_lf_only(self):
        self.append("--op", "ingest", "--note", "Łąka/Żółw.md")
        self.append("--op", "learn", "--count", "score=4", at="2026-11-28T08:00")
        data = self.log.read_bytes()
        self.assertNotIn(b"\r", data)
        self.assertEqual(data.count(b"\n"), 6)
        self.assertIn("`Łąka/Żółw.md`".encode("utf-8"), data)

    def test_default_time_is_now_utc(self):
        before = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        code, _, err = self.append("--op", "ingest", at=None)
        after = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        self.assertEqual(code, 0, err)
        when = self.read()[0]["time"]
        self.assertTrue(before <= when <= after, (before, when, after))


class TestPrivacy(VaultCase):
    @needs_privacy
    def test_private_folder_masked(self):
        self.privacy()
        code, out, err = self.append(
            "--op", "ingest",
            "--note", "CLIENTS/acme-labs/Plan.md",
            "--note", "CLIENTS\\Acme Labs\\Kickoff.md",
            "--note", "NOTES/acme_labs.md",
            "--note", "TOOLS/Acmelabsoft.md",          # the term inside a longer word
            "--note", "TOOLS/Labs.md")
        self.assertEqual(code, 0, err)
        self.assertEqual(err, "")
        self.assertEqual(self.read()[0]["notes"], [
            "CLIENTS/[private]/Plan.md",
            "CLIENTS/[private]/Kickoff.md",
            "NOTES/[private]",
            "TOOLS/Acmelabsoft.md",
            "TOOLS/Labs.md"])
        data = self.log.read_bytes().lower()
        self.assertNotIn(b"acme-labs", data)
        self.assertNotIn(b"acme labs", data)
        self.assertNotIn(b"acme-labs", out.lower().encode("utf-8"))

    @needs_privacy
    def test_committed_privacy_file_and_diacritics(self):
        (self.root / "content" / "_privacy.md").write_text(
            "# Privacy\n\n## Always cut\n\n- \"Łąka Wiśnia\" — a person\n\n"
            "## Exceptions\n\n- \"Public Name\"\n", encoding="utf-8")
        self.append("--op", "watch", "--note", "PEOPLE/laka-wisnia/Notes.md",
                    "--note", "PEOPLE/Public Name.md")
        self.assertEqual(self.read()[0]["notes"],
                         ["PEOPLE/[private]/Notes.md", "PEOPLE/Public Name.md"])

    @needs_privacy
    def test_term_across_segments_masks_the_whole_path(self):
        self.privacy("## Always cut\n\n- \"Acme/Labs\"\n")
        self.append("--op", "ingest", "--note", "CLIENTS/Acme/Labs/Plan.md")
        self.assertEqual(self.read()[0]["notes"], ["[private]"])

    def test_privacy_script_missing(self):
        self.privacy()
        with tempfile.TemporaryDirectory() as empty:
            err = io.StringIO()
            with mock.patch.object(oplog, "PRIVACY_DIR", Path(empty)), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = oplog.main(["--root", str(self.root), "append", "--op", "ingest",
                                   "--note", "CLIENTS/acme-labs/Plan.md",
                                   "--at", "2026-11-27T14:03"])
        self.assertEqual(code, 0)
        self.assertEqual(err.getvalue(), oplog.NOTICE + "\n")
        self.assertEqual(self.read()[0]["notes"], ["CLIENTS/acme-labs/Plan.md"])

    @needs_privacy
    def test_privacy_script_present_again_after_missing(self):
        # Loaded on every call: a test that patched the path leaves nothing cached.
        self.privacy()
        self.append("--op", "ingest", "--note", "CLIENTS/acme-labs/Plan.md")
        self.assertEqual(self.read()[0]["notes"], ["CLIENTS/[private]/Plan.md"])

    @needs_privacy
    def test_unreadable_privacy_file_writes_nothing(self):
        (self.root / "content" / "_privacy.local.md").write_bytes(b"## Always cut\n\n- \xff\xfe\n")
        code, _, err = self.append("--op", "ingest", "--note", "CLIENTS/acme-labs/Plan.md")
        self.assertEqual(code, 1)
        self.assertIn("error", err)
        self.assertFalse(self.log.exists())


class TestRead(VaultCase):
    def test_missing_file(self):
        self.assertEqual(self.read(), [])

    def test_out_of_order_rows_malformed_lines_and_since(self):
        self.log.parent.mkdir()
        self.log.write_bytes(HEADER + (
            "| 2026-11-20 10:00 | ingest | sources=2 created=1 | `A.md`, `B.md` |\n"
            "| 2026-11-03 09:15 | enhance | updated=1 | `C.md` |\n"
            "Hand-written: moved D by hand\n"
            "| 2026-11-10 | curate | retired=1 | - |\n"              # no time
            "| 2026-13-01 10:00 | curate | retired=1 | - |\n"        # no such month
            "| 2026-11-11 10:00 | Curate | retired=1 | - |\n"        # bad operation
            "| 2026-11-12 10:00 | curate | summary=great | - |\n"    # free text in What
            "| 2026-11-13 10:00 | curate | - | A.md |\n"              # path not a code span
            "| 2026-11-14 10:00 | curate | - |\n"                     # a cell short
            "| 2026-11-01 23:59 | compile | created=3 | `E.md` |\r\n"
            "| 2026-11-25 07:00 | review | days=7 | - |\n"
            "| 2026-11-20 10:00 | learn | score=3 | `F.md` and 2 more |"   # no final newline
        ).encode("utf-8"))
        rows = self.read()
        self.assertEqual([(r["time"], r["op"]) for r in rows], [
            ("2026-11-01 23:59", "compile"),
            ("2026-11-03 09:15", "enhance"),
            ("2026-11-20 10:00", "ingest"),
            ("2026-11-20 10:00", "learn"),
            ("2026-11-25 07:00", "review")])
        self.assertEqual(rows[2]["counts"], {"sources": 2, "created": 1})
        self.assertEqual(rows[2]["notes"], ["A.md", "B.md"])
        self.assertEqual((rows[3]["notes"], rows[3]["more"]), (["F.md"], 2))
        since = self.read("--since", "2026-11-03")
        self.assertEqual([r["op"] for r in since], ["enhance", "ingest", "learn", "review"])
        window = self.read("--since", "2026-11-02", "--until", "2026-11-20")
        self.assertEqual([r["op"] for r in window], ["enhance", "ingest", "learn"])
        self.assertEqual(self.read("--until", "2026-11-01"), [rows[0]])

    def test_bad_dates_refused(self):
        for args in (["--since", "2026-11-3"], ["--until", "2026-02-30"], ["--since", "yesterday"]):
            with self.subTest(args=args):
                code, out, err = run(self.root, "read", *args)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")

    def test_non_ascii_round_trip(self):
        self.append("--op", "ingest", "--note", "PODRÓŻE/Kraków — plan.md")
        self.assertEqual(self.read()[0]["notes"], ["PODRÓŻE/Kraków — plan.md"])


class TestSlug(VaultCase):
    def slug(self, text):
        code, out, err = run(self.root, "slug", text)
        self.assertEqual(code, 0, err)
        return out.strip()

    def test_folding(self):
        self.assertEqual(self.slug("Łódź i Żółw: Agent Memory!"), "lodz-i-zolw-agent-memory")
        self.assertEqual(self.slug("  Crème brûlée -- Straße  "), "creme-brulee-stra-e")
        self.assertEqual(self.slug("[[AI/Retrieval-Augmented Generation]]"),
                         "ai-retrieval-augmented-generation")

    def test_length(self):
        slug = self.slug("word " * 30)
        self.assertLessEqual(len(slug), 60)
        self.assertEqual(slug, "-".join(["word"] * 12))  # 59 characters, no "-" at the end

    def test_empty(self):
        self.assertEqual(self.slug(""), "topic")
        self.assertEqual(self.slug("!!! ??? ..."), "topic")
        self.assertEqual(self.slug("日本語"), "topic")

    @needs_privacy
    def test_private(self):
        self.privacy()
        self.assertEqual(self.slug("Pricing for Acme Labs"), "private")
        self.assertEqual(self.slug("acme.labs onboarding"), "private")  # its slug holds acme-labs
        self.assertEqual(self.slug("Acmelabsoft pricing"), "acmelabsoft-pricing")

    def test_private_check_unavailable(self):
        self.privacy()
        err = io.StringIO()
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as empty:
            with mock.patch.object(oplog, "PRIVACY_DIR", Path(empty)), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = oplog.main(["slug", "--root", str(self.root), "Acme Labs"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue(), "acme-labs\n")
        self.assertEqual(err.getvalue(), oplog.NOTICE + "\n")


if __name__ == "__main__":
    unittest.main()
