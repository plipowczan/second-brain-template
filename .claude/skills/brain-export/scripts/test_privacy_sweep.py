#!/usr/bin/env python3
"""Tests for privacy_sweep.py — run: python .claude/skills/brain-export/scripts/test_privacy_sweep.py"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "privacy_sweep.py"
WATCH = Path(__file__).resolve().parents[2] / "brain-watch" / "scripts" / "watch.py"

sys.path.insert(0, str(Path(__file__).parent))
import privacy_sweep  # noqa: E402

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

# A committed _privacy.md: one live term, one commented-out example, an exception.
PRIVACY_MD = (
    "# Privacy rules for /export --public\n\n"
    "## Always cut (extends the defaults)\n\n"
    "<!-- - \"Project Falcon\" — internal codename -->\n"
    "- \"Acme Corp\" — client, under NDA\n\n"
    "## Exceptions (overrides the defaults)\n\n"
    "- \"Public Name\" — my brand\n"
)
# The git-ignored _privacy.local.md: unquoted, curly-quoted, non-Latin, commented block.
LOCAL_MD = (
    "## Always cut\n\n"
    "- Zed — client\n"
    "- “Żabka Polska” — client\n"
    "<!--\n- \"Hidden Client\"\n-->\n\n"
    "## Notes\n\n- \"Not A Term\"\n"
)


def vault(td, privacy=None, local=None):
    """A vault root under td with the given privacy files; returns its path."""
    root = Path(td) / "vault"
    (root / "content").mkdir(parents=True, exist_ok=True)
    if privacy is not None:
        (root / "content" / "_privacy.md").write_text(privacy, encoding="utf-8")
    if local is not None:
        (root / "content" / "_privacy.local.md").write_text(local, encoding="utf-8")
    return root


def run(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                       capture_output=True, encoding="utf-8")
    return r.returncode, r.stdout


def sweep(tmpdir, root=None):
    """Sweep tmpdir; with no root, against a vault (inside tmpdir, holding no .md files)
    that has no privacy files."""
    if root is None:
        root = vault(tmpdir)
    code, out = run("--root", root, tmpdir)
    return code, json.loads(out)


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

    def test_bad_arguments_are_usage_errors(self):
        with tempfile.TemporaryDirectory() as td:
            root = vault(td)
            for args in (["--root", root, "--terms", td], ["--root", root, td, td],
                         ["--root", root, "--bogus", td], [td, "--root"]):
                self.assertEqual(run(*args)[0], 1, args)

    def test_no_content_dir_is_a_usage_error(self):
        # From the wrong directory the private terms would silently be missing.
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "note.md").write_text("plain", encoding="utf-8")
            self.assertEqual(run("--root", td, td)[0], 1)
            self.assertEqual(run("--root", td, "--terms")[0], 1)


class PrivateTermsTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = vault(self.td.name, PRIVACY_MD, LOCAL_MD)
        self.staging = Path(self.td.name) / "staging"
        self.staging.mkdir()

    def tearDown(self):
        self.td.cleanup()

    def note(self, rel, text):
        p = self.staging / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_terms_come_from_both_files(self):
        code, out = run("--root", self.root, "--terms")
        self.assertEqual(code, 0)
        out = json.loads(out)
        self.assertEqual([t["term"] for t in out["terms"]], ["Acme Corp", "Zed", "Żabka Polska"])
        self.assertEqual(out["sources"], {"_privacy.md": 1, "_privacy.local.md": 2})
        acme = out["terms"][0]["forms"]
        self.assertEqual(acme, sorted(["Acme Corp", "AcmeCorp", "Acme-Corp", "Acme_Corp"]))

    def test_a_missing_file_counts_as_null(self):
        root = vault(Path(self.td.name) / "other", PRIVACY_MD)
        out = json.loads(run("--root", root, "--terms")[1])
        self.assertEqual(out["sources"], {"_privacy.md": 1, "_privacy.local.md": None})
        self.note("a.md", "plain")
        self.assertEqual(sweep(self.staging, root)[1]["terms"],
                         {"_privacy.md": 1, "_privacy.local.md": None})

    def test_local_term_is_a_hit_in_every_form(self):
        lines = ["built for ACME CORP in 2026", "https://github.com/acmecorp/tools",
                 "see acme-corp.com", "tags: [acme_corp]", "Zed asked for it",
                 "spotkanie w żabka polska", "[[Żabka-Polska rollout]]"]
        self.note("AI/TOOLS/Tool.md", "\n".join(lines) + "\n")
        code, out = sweep(self.staging, self.root)
        self.assertEqual(code, 2)
        terms = [h for h in out["hits"] if h["class"] == "private-term"]
        self.assertEqual([h["line"] for h in terms], list(range(1, len(lines) + 1)))
        self.assertTrue(all("[private]" in h["context"] for h in terms), terms)

    def test_no_term_leaks_into_the_output(self):
        self.note("a.md", "Acme Corp and Zed, mail ops@acme-corp.com, Żabka Polska\n")
        # A long line is cut around the hit: the term must be masked in the cut too.
        self.note("b.md", "a" * 150 + " Acme Corp " + "b" * 25 + " x@y.pl " + "c" * 80 + "\n")
        code, out = run("--root", self.root, self.staging)
        self.assertEqual(code, 2)
        low = out.lower()
        for leak in ("acme", "zed", "żabka"):
            self.assertNotIn(leak, low)
        self.assertIn("email", out)          # the email hit is reported, masked

    def test_no_hit_inside_a_word_or_from_other_sections(self):
        self.note("a.md", "Zedboard is a board\nProject Falcon shipped\n"
                          "Hidden Client called\nPublic Name and Not A Term\n")
        code, out = sweep(self.staging, self.root)
        self.assertEqual(code, 0, out["hits"])

    def test_a_path_with_a_term_is_a_hit(self):
        self.note("PROJECTS/acme-corp/Plan.md", "nothing private in the body\n")
        code, out = sweep(self.staging, self.root)
        self.assertEqual(code, 2)
        self.assertEqual([(h["line"], h["class"]) for h in out["hits"]], [(0, "private-term")])

    def test_private_terms_api(self):
        terms = privacy_sweep.private_terms(self.root)
        self.assertEqual(terms, ["Acme Corp", "Zed", "Żabka Polska"])
        self.assertTrue(privacy_sweep.private_hit("built for acme corp", terms))
        self.assertFalse(privacy_sweep.private_hit("Zedboard", terms))
        self.assertEqual(privacy_sweep.mask("ACME-CORP and Zed", terms), "[private] and [private]")

    @unittest.skipUnless(WATCH.exists(), "brain-watch is not installed next to brain-export")
    def test_same_terms_and_matches_as_brain_watch(self):
        try:
            spec = importlib.util.spec_from_file_location("watch_for_export_test", WATCH)
            watch = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(watch)
        except ImportError as e:      # watch.py needs PyYAML (requirements.txt)
            self.skipTest(f"cannot import brain-watch: {e}")
        self.assertEqual(privacy_sweep.private_terms(self.root), watch.private_terms(self.root))
        terms = watch.private_terms(self.root)
        for t in terms + ["Acme  Labs", "a_b-c d"]:
            self.assertEqual(privacy_sweep.term_forms(t), watch.term_forms(t), t)
        for text in ["built for acme corp", "acmecorp.io", "ACME_CORP", "Zedboard", "zed",
                     "x_zed_y", "żabka-polska", "Acme Corporation", "nothing here", ""]:
            self.assertEqual(privacy_sweep.private_hit(text, terms),
                             watch.private_hit(text, terms), text)
            self.assertEqual(privacy_sweep.mask(text, terms), watch.redact(text, terms), text)


if __name__ == "__main__":
    unittest.main()
