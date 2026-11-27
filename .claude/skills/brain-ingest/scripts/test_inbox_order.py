#!/usr/bin/env python3
"""Tests for inbox_order.py — run from this folder: python -m unittest test_inbox_order"""

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "inbox_order.py"

sys.path.insert(0, str(HERE))
import inbox_order  # noqa: E402

INBOX = "content/_raw/inbox/"


def ts(*parts):
    return datetime(*parts, tzinfo=timezone.utc).timestamp()


def nfc(value):
    """value with every string NFC-normalised (macOS may hand back NFD file names)."""
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [nfc(v) for v in value]
    if isinstance(value, dict):
        return {k: nfc(v) for k, v in value.items()}
    return value


class InboxCase(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        self.inbox = self.root / "content" / "_raw" / "inbox"
        self.inbox.mkdir(parents=True)
        self.processed = self.root / "content" / "_raw" / "processed"
        self.processed.mkdir()

    def tearDown(self):
        self._td.cleanup()

    def put(self, rel, data="Some text.\n", mtime=None, folder=None):
        path = (folder or self.inbox) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            data = data.encode("utf-8")
        path.write_bytes(data)
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path

    def listing(self, *args):
        """Run inbox_order.py as the skill does: from the vault root, no --root."""
        p = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=str(self.root),
                           capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8"))
        return nfc(json.loads(p.stdout.decode("utf-8")))

    def paths(self, result):
        return [s["path"][len(INBOX):] for s in result["sources"]]


class TestOrder(InboxCase):
    def test_date_in_name(self):
        # Modification times say the opposite, and lose: the name comes first.
        self.put("2026-03-02_call.md", mtime=ts(2024, 1, 1))
        self.put("2025-11-20_notes.md", mtime=ts(2026, 6, 1))
        result = self.listing()
        self.assertEqual(self.paths(result), ["2025-11-20_notes.md", "2026-03-02_call.md"])
        self.assertEqual([(s["basis"], s["key"]) for s in result["sources"]],
                         [("name", "2025-11-20"), ("name", "2026-03-02")])

    def test_frontmatter_date(self):
        self.put("b.md", "---\ntitle: B\ndate: 2025-02-01\n---\nBody\n", mtime=ts(2020, 1, 1))
        self.put("a.md", "---\ndate: \"2025-03-01\"\n---\nBody\n", mtime=ts(2020, 1, 1))
        self.put("c.md", "﻿---\r\ndate: '2025-01-15 10:30'\r\n---\r\nBody\r\n",
                 mtime=ts(2020, 1, 1))
        self.put("d.md", "---\ndate: 2025-01-15T09:00:00+02:00 # local\n---\nBody\n",
                 mtime=ts(2020, 1, 1))
        result = self.listing()
        self.assertEqual(self.paths(result), ["d.md", "c.md", "b.md", "a.md"])
        self.assertEqual([(s["basis"], s["key"]) for s in result["sources"]], [
            ("frontmatter", "2025-01-15T07:00:00Z"),
            ("frontmatter", "2025-01-15T10:30:00Z"),
            ("frontmatter", "2025-02-01"),
            ("frontmatter", "2025-03-01")])

    def test_frontmatter_only_at_the_start_and_in_the_first_lines(self):
        self.put("late.md", "Intro\n---\ndate: 2020-01-01\n---\n", mtime=ts(2025, 5, 5))
        self.put("body.md", "---\ntitle: X\n---\ndate: 2020-01-01\n", mtime=ts(2025, 5, 6))
        self.put("deep.md", "---\n" + "k: v\n" * 60 + "date: 2020-01-01\n---\n",
                 mtime=ts(2025, 5, 7))
        self.put("nested.md", "---\nmeta:\n  date: 2020-01-01\n---\n", mtime=ts(2025, 5, 8))
        self.put("bad.md", "---\ndate: 2020-13-01\n---\n", mtime=ts(2025, 5, 9))
        result = self.listing()
        self.assertEqual({s["basis"] for s in result["sources"]}, {"mtime"})
        self.assertEqual(self.paths(result), ["late.md", "body.md", "deep.md", "nested.md", "bad.md"])

    def test_mtime(self):
        self.put("later.txt", mtime=ts(2025, 4, 2, 8, 0, 0))
        self.put("earlier.pdf", b"%PDF-1.4 binary", mtime=ts(2025, 4, 1, 23, 59, 30))
        result = self.listing()
        self.assertEqual(self.paths(result), ["earlier.pdf", "later.txt"])
        self.assertEqual([(s["basis"], s["key"]) for s in result["sources"]],
                         [("mtime", "2025-04-01T23:59:30Z"), ("mtime", "2025-04-02T08:00:00Z")])

    def test_mixed_bases(self):
        self.put("2025-06-01 talk.md", mtime=ts(2020, 1, 1))
        self.put("article.md", "---\ndate: 2025-03-01\n---\nText\n", mtime=ts(2030, 1, 1))
        self.put("clip.html", "<p>x</p>", mtime=ts(2025, 4, 1, 12, 0))
        self.put("same-day.md", "---\ndate: 2025-06-01 00:00\n---\nText\n")
        result = self.listing()
        self.assertEqual(self.paths(result),
                         ["article.md", "clip.html", "2025-06-01 talk.md", "same-day.md"])
        self.assertEqual([s["basis"] for s in result["sources"]],
                         ["frontmatter", "mtime", "name", "frontmatter"])

    def test_ties_by_path(self):
        self.put("2025-01-01 b.md")
        self.put("2025-01-01 A.md")
        self.put("c.md", "---\ndate: 2025-01-01\n---\n")
        self.put("sub/2025-01-01 a2.md")
        self.put("d.md", mtime=ts(2025, 1, 1))
        result = self.listing()
        self.assertEqual(self.paths(result),
                         ["2025-01-01 A.md", "2025-01-01 b.md", "c.md", "d.md", "sub/2025-01-01 a2.md"])

    def test_invalid_date_in_name_ignored(self):
        self.put("2026-13-40 notes.md", mtime=ts(2025, 2, 2))
        self.put("2026-02-30_2025-02-03.md")
        self.put("v12025-01-01.md", mtime=ts(2025, 2, 4))  # digits run on: not a date
        result = self.listing()
        self.assertEqual([(p, s["basis"], s["key"]) for p, s in zip(self.paths(result), result["sources"])], [
            ("2026-13-40 notes.md", "mtime", "2025-02-02T00:00:00Z"),
            ("2026-02-30_2025-02-03.md", "name", "2025-02-03"),
            ("v12025-01-01.md", "mtime", "2025-02-04T00:00:00Z")])


class TestKinds(InboxCase):
    def test_attachments_told_apart(self):
        self.put("transcript.md", "See ![[shot1.png]]\n")
        for name in ("shot1.png", "Shot2.JPG", "diagram.svg", "clip.MP4", "voice.m4a",
                     "photo.heic", "empty.png"):
            self.put(name, b"" if name == "empty.png" else b"\x89PNG")
        self.put("paper.pdf", b"%PDF-1.7")
        self.put("data.csv", "a,b\n1,2\n")
        result = self.listing()
        self.assertEqual(sorted(self.paths(result)), ["data.csv", "paper.pdf", "transcript.md"])
        # An empty attachment is still an attachment: only sources are checked.
        self.assertEqual(result["attachments"], [INBOX + n for n in (
            "clip.MP4", "diagram.svg", "empty.png", "photo.heic", "shot1.png", "Shot2.JPG",
            "voice.m4a")])
        self.assertEqual(result["unusable"], [])

    def test_unusable(self):
        self.put("2020-01-01 empty.md", b"")
        self.put("blank.txt", " \n\t\r\n  \n")
        self.put("bom-only.md", b"\xef\xbb\xbf\n \n")
        self.put("nbsp.html", " 　\n")
        self.put("spaces.pdf", b"   ")          # not a text type: a source
        self.put("real.md", "Text\n")
        result = self.listing("--limit", "1")
        self.assertEqual(result["unusable"], [
            {"path": INBOX + "2020-01-01 empty.md", "reason": "empty"},
            {"path": INBOX + "blank.txt", "reason": "empty"},
            {"path": INBOX + "bom-only.md", "reason": "empty"},
            {"path": INBOX + "nbsp.html", "reason": "empty"}])
        self.assertEqual(sorted(self.paths(result)), ["real.md", "spaces.pdf"])
        self.assertEqual(len(result["take"]), 1)
        self.assertEqual(result["remaining"], 1)

    def test_unreadable(self):
        self.put("2020-01-01 locked.md", "Text\n")
        self.put("open.md", "Text\n")
        real_open = open

        def fake_open(file, *args, **kwargs):
            if Path(file).name == "2020-01-01 locked.md":
                raise PermissionError(13, "Permission denied", str(file))
            return real_open(file, *args, **kwargs)

        out = io.StringIO()
        with mock.patch.object(inbox_order, "open", fake_open, create=True), \
                contextlib.redirect_stdout(out):
            code = inbox_order.main(["--root", str(self.root)])
        self.assertEqual(code, 0)
        result = nfc(json.loads(out.getvalue()))
        self.assertEqual(result["unusable"],
                         [{"path": INBOX + "2020-01-01 locked.md", "reason": "unreadable"}])
        self.assertEqual(self.paths(result), ["open.md"])
        self.assertEqual((result["take"], result["remaining"]), ([INBOX + "open.md"], 0))

    def test_hidden_skipped(self):
        self.put(".gitkeep", b"")
        self.put(".hidden.md", "Text\n")
        self.put(".obsidian/workspace.json", "{}")
        self.put(".trash/old.md", "Text\n")
        self.put("sub/.DS_Store", b"\x00\x01")
        self.put("sub/kept.md", "Text\n")
        result = self.listing()
        self.assertEqual(self.paths(result), ["sub/kept.md"])
        self.assertEqual((result["attachments"], result["unusable"]), ([], []))

    def test_non_ascii_names(self):
        self.put("podróże/2025-05-01 Łódź — notatki.md", "Tekst\n")
        self.put("Zażółć gęślą jaźń.txt", "Tekst\n", mtime=ts(2025, 1, 1))
        self.put("zrzut ekranu ąę.PNG", b"\x89PNG")
        result = self.listing()
        self.assertEqual(self.paths(result),
                         ["Zażółć gęślą jaźń.txt", "podróże/2025-05-01 Łódź — notatki.md"])
        self.assertEqual(result["attachments"], [INBOX + "zrzut ekranu ąę.PNG"])
        self.assertTrue(all("\\" not in s["path"] for s in result["sources"]))


class TestDuplicates(InboxCase):
    def test_found_in_a_nested_processed_folder(self):
        body = "Transcript of the call.\n"
        self.put("2025-03-01 call.md", body)
        self.put("fresh.md", "Something new.\n")
        self.put("2025/03/2025-03-02_call.md", body, folder=self.processed)
        self.put("2025/01/2025-03-02_call.md", body, folder=self.processed)  # first by path
        self.put("2025/01/other.md", "Transcript of the call!\n", folder=self.processed)  # same size
        self.put(".hidden/copy.md", body, folder=self.processed)
        result = self.listing()
        dup = {s["path"][len(INBOX):]: s["duplicate_of"] for s in result["sources"]}
        self.assertEqual(dup, {"2025-03-01 call.md": "content/_raw/processed/2025/01/2025-03-02_call.md",
                               "fresh.md": None})

    def test_binary_duplicate(self):
        data = bytes(range(256)) * 5000  # bigger than one read
        self.put("paper.pdf", data)
        self.put("paper.pdf", data, folder=self.processed / "2024")
        result = self.listing()
        self.assertEqual(result["sources"][0]["duplicate_of"], "content/_raw/processed/2024/paper.pdf")
        self.assertEqual(hashlib.sha256(data).hexdigest(), inbox_order.sha256(self.inbox / "paper.pdf"))

    def test_no_processed_folder(self):
        self.processed.rmdir()
        self.put("a.md")
        self.assertIsNone(self.listing()["sources"][0]["duplicate_of"])


class TestLimit(InboxCase):
    def setUp(self):
        super().setUp()
        for day in (5, 3, 1, 4, 2):
            self.put(f"2025-01-0{day} s.md")
        self.put("img.png", b"\x89PNG")
        self.put("empty.md", b"")

    def test_limit_and_remaining(self):
        result = self.listing("--limit", "2")
        self.assertEqual(result["take"], [INBOX + "2025-01-01 s.md", INBOX + "2025-01-02 s.md"])
        self.assertEqual(result["remaining"], 3)
        self.assertEqual(len(result["sources"]), 5)

    def test_without_limit_takes_all(self):
        result = self.listing()
        self.assertEqual(result["take"], [s["path"] for s in result["sources"]])
        self.assertEqual(result["remaining"], 0)

    def test_limit_above_count(self):
        result = self.listing("--limit", "10")
        self.assertEqual((len(result["take"]), result["remaining"]), (5, 0))

    def test_bad_limit(self):
        for value in ("0", "-1", "two", "1.5"):
            with self.subTest(value=value):
                p = subprocess.run([sys.executable, str(SCRIPT), "--limit", value],
                                   cwd=str(self.root), capture_output=True)
                self.assertEqual(p.returncode, 2)
                self.assertEqual(p.stdout, b"")


class TestEmpty(unittest.TestCase):
    EMPTY = {"sources": [], "attachments": [], "unusable": [], "take": [], "remaining": 0}

    def run_in(self, root, *args):
        p = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=str(root), capture_output=True)
        return p.returncode, p.stdout.decode("utf-8"), p.stderr.decode("utf-8")

    def test_missing_inbox(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "content").mkdir()
            code, out, err = self.run_in(td, "--limit", "3")
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out), self.EMPTY)

    def test_empty_inbox(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "content" / "_raw" / "inbox").mkdir(parents=True)
            (Path(td) / "content" / "_raw" / "inbox" / ".gitkeep").write_bytes(b"")
            code, out, err = self.run_in(td)
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out), self.EMPTY)

    def test_root_flag_and_no_content(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as elsewhere:
            inbox = Path(td) / "content" / "_raw" / "inbox"
            inbox.mkdir(parents=True)
            (inbox / "a.md").write_text("Text\n", encoding="utf-8")
            code, out, err = self.run_in(elsewhere, "--root", td)
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["take"], [INBOX + "a.md"])
            code, out, err = self.run_in(elsewhere)
            self.assertEqual((code, out), (1, ""))
            self.assertIn("no content/", err)


if __name__ == "__main__":
    unittest.main()
