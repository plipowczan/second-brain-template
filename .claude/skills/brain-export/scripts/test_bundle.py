#!/usr/bin/env python3
"""Tests for bundle.py — run from repo root: python .claude/skills/brain-export/scripts/test_bundle.py"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "bundle.py"


def run(args, cwd):
    return subprocess.run([sys.executable, str(SCRIPT)] + args,
                          capture_output=True, text=True, cwd=cwd)


class BundleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "content/AI/TOOLS").mkdir(parents=True)
        (self.root / "content/AI/TOOLS/Serena.md").write_text(
            '---\ntitle: "Serena"\ntags: ["tool"]\n---\n\nBody [[GrepRAG]].\n', encoding="utf-8")
        (self.root / "content/_indexes").mkdir()
        (self.root / "content/_indexes/catalog.md").write_text("# Note Catalog\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def pack(self, paths, out="pack.zip"):
        return run(["pack", "--source", "test-brain", "--out", out] + paths, self.root)

    def test_pack_unpack_roundtrip(self):
        r = self.pack(["AI/TOOLS/Serena.md"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["packed"], 1)

        with zipfile.ZipFile(self.root / "pack.zip") as zf:
            self.assertEqual(sorted(zf.namelist()),
                             ["manifest.json", "notes/AI/TOOLS/Serena.md"])
            manifest = json.loads(zf.read("manifest.json"))
        self.assertEqual(manifest["format"], 1)
        self.assertEqual(manifest["source"], "test-brain")
        self.assertEqual(manifest["notes"][0]["title"], "Serena")

        r = run(["unpack", "--bundle", "pack.zip", "--dest", "staging"], self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = json.loads(r.stdout)
        self.assertTrue(out["ok"])
        extracted = self.root / "staging/notes/AI/TOOLS/Serena.md"
        self.assertEqual(extracted.read_bytes(),
                         (self.root / "content/AI/TOOLS/Serena.md").read_bytes())

    def test_pack_excludes_protected_and_non_md(self):
        r = self.pack(["AI/TOOLS/Serena.md", "_indexes/catalog.md"])
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["packed"], 1)
        self.assertEqual(out["skipped_excluded"], ["_indexes/catalog.md"])

    def test_pack_excludes_underscore_files_anywhere(self):
        (self.root / "content/_privacy.md").write_text("secret rules", encoding="utf-8")
        (self.root / "content/AI/_drafts").mkdir()
        (self.root / "content/AI/_drafts/wip.md").write_text("draft", encoding="utf-8")
        r = self.pack(["AI/TOOLS/Serena.md", "_privacy.md", "AI/_drafts/wip.md"])
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["packed"], 1)
        self.assertEqual(sorted(out["skipped_excluded"]),
                         ["AI/_drafts/wip.md", "_privacy.md"])

    def test_pack_empty_selection_fails(self):
        r = self.pack(["_indexes/catalog.md"])
        self.assertEqual(r.returncode, 1)

    def test_unpack_rejects_tampered_hash(self):
        self.pack(["AI/TOOLS/Serena.md"])
        # rewrite note inside zip without updating manifest
        src = self.root / "pack.zip"
        bad = self.root / "bad.zip"
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(bad, "w") as zout:
            zout.writestr("manifest.json", zin.read("manifest.json"))
            zout.writestr("notes/AI/TOOLS/Serena.md", b"tampered")
        r = run(["unpack", "--bundle", "bad.zip", "--dest", "staging2"], self.root)
        self.assertEqual(r.returncode, 2)
        self.assertIn("sha256 mismatch", r.stdout)

    def test_unpack_rejects_unknown_format(self):
        bad = self.root / "fmt.zip"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"format": 99, "notes": []}))
        r = run(["unpack", "--bundle", "fmt.zip", "--dest", "staging3"], self.root)
        self.assertEqual(r.returncode, 2)
        self.assertIn("unsupported bundle format", r.stdout)

    def test_unpack_rejects_zip_slip(self):
        for evil in ("../evil.md", "/abs/evil.md", "a/../../evil.md", "C:/evil.md"):
            bad = self.root / "slip.zip"
            with zipfile.ZipFile(bad, "w") as zf:
                zf.writestr("manifest.json", json.dumps({
                    "format": 1, "source": "x", "exported": "2026-07-11",
                    "notes": [{"path": evil, "title": "evil",
                               "sha256": "0" * 64}]}))
                zf.writestr("notes/" + evil, b"pwned")
            r = run(["unpack", "--bundle", "slip.zip", "--dest", "slipstage"], self.root)
            self.assertEqual(r.returncode, 2, f"{evil}: {r.stdout}")
            self.assertIn("unsafe", r.stdout)
            self.assertFalse((self.root.parent / "evil.md").exists())
            self.assertFalse(Path("C:/evil.md").exists())

    def test_same_normalizes_newlines(self):
        a = self.root / "a.md"
        b = self.root / "b.md"
        a.write_bytes(b"line1\nline2\n")
        b.write_bytes(b"line1\r\nline2\r\n")
        r = run(["same", "a.md", "b.md"], self.root)
        self.assertTrue(json.loads(r.stdout)["same"])
        b.write_bytes(b"line1\r\nline2 changed\r\n")
        r = run(["same", "a.md", "b.md"], self.root)
        self.assertFalse(json.loads(r.stdout)["same"])


if __name__ == "__main__":
    unittest.main()
