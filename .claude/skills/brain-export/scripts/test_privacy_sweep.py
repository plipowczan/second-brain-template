#!/usr/bin/env python3
"""Tests for privacy_sweep.py — run: python .claude/skills/brain-export/scripts/test_privacy_sweep.py"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "privacy_sweep.py"

POSITIVE = {
    "email": "contact me at jan.kowalski@example.com please",
    "phone": "call +48 601 234 567 tomorrow",
    "phone-grouped": "numer 601-234-567 stacjonarny",
    "iban": "przelew na PL61 1090 1014 0000 0712 1981 2874",
    "card": "card 4111 1111 1111 1111 expires soon",
    "api-key": "export OPENAI_KEY=sk-abc123def456ghi789jkl012",
    "api-key-aws": "AKIAIOSFODNN7EXAMPLE is the access key",
    "jwt": "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkifQ.SflKxwRJSMeKKF2QT4fwpM",
    "btc-wallet": "send to bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",
    "eth-wallet": "wallet 0x742d35Cc6634C0532925a3b844Bc454e4438f44e ok",
}

NEGATIVE = {
    "arxiv-not-phone": "see arXiv 2410.14684 and 2601.23254 for details",
    "sha256-not-key": "sha256: 318f206dead2f2422a20304179f37937cefaf06d9326278cdcd8e05882b1556f",
    "date-not-card": "spotkanie 2026-07-12 o 10:30",
    "version-not-phone": "upgraded from 1.2.3 to 4.5.6 yesterday",
    "plain-prose": "installed Serena via uv tool install, wired into Claude Code",
    "wikilink": "see [[Structural Retrieval for Code]] and [[GrepRAG]]",
}


def sweep(tmpdir):
    r = subprocess.run([sys.executable, str(SCRIPT), str(tmpdir)],
                       capture_output=True, text=True)
    return r.returncode, json.loads(r.stdout)


class SweepTest(unittest.TestCase):
    def test_positive_each_class_detected(self):
        for name, text in POSITIVE.items():
            with tempfile.TemporaryDirectory() as td:
                (Path(td) / "note.md").write_text(text, encoding="utf-8")
                code, out = sweep(td)
                self.assertEqual(code, 2, f"{name}: expected hit, got clean")
                self.assertFalse(out["clean"], name)
                self.assertGreaterEqual(len(out["hits"]), 1, name)

    def test_negative_no_false_positives(self):
        with tempfile.TemporaryDirectory() as td:
            for name, text in NEGATIVE.items():
                (Path(td) / f"{name}.md").write_text(text, encoding="utf-8")
            code, out = sweep(td)
            self.assertEqual(code, 0, f"false positives: {out['hits']}")
            self.assertTrue(out["clean"])
            self.assertEqual(out["files_scanned"], len(NEGATIVE))

    def test_hit_reports_location_and_class(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "sub").mkdir()
            (Path(td) / "sub" / "leak.md").write_text(
                "line one\nmail: x@y.pl\n", encoding="utf-8")
            code, out = sweep(td)
            self.assertEqual(code, 2)
            hit = out["hits"][0]
            self.assertEqual((hit["file"], hit["line"], hit["class"]),
                             ("sub/leak.md", 2, "email"))

    def test_usage_error(self):
        r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
