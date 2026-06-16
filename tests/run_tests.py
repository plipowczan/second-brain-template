#!/usr/bin/env python3
"""Integration self-tests for the KB template skills. Builds a throwaway temp vault
and exercises build_indexes, lint_scan, lint_links, gaps, and refactor end to end.
Run from anywhere:  python tests/run_tests.py   (exit 0 = all pass)."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
BUILD = SKILLS / "reindex" / "scripts" / "build_indexes.py"
LINT_SCAN = SKILLS / "lint" / "scripts" / "lint_scan.py"
LINT_LINKS = SKILLS / "lint" / "scripts" / "lint_links.py"
REFACTOR = SKILLS / "refactor" / "scripts" / "refactor.py"
GAPS = SKILLS / "gaps" / "scripts" / "gaps.py"

PAD = " padding" * 30
NOTE_A = ('---\ntitle: "Alpha"\ndate: 2026-01-01\ntags: ["x"]\ntype: knowledge-note\n'
          'summary: "Alpha note."\n---\n# Alpha\nLinks to [[Beta]] and a code span '
          '`[[NotARealLink]]`.\n' + PAD)
NOTE_B = ('---\ntitle: "Beta"\ndate: 2026-01-01\ntags: ["x"]\ntype: knowledge-note\n'
          'summary: "Beta note."\n---\n# Beta\nLinks back to [[Alpha]].\n' + PAD)

failures = []


def check(name, cond, detail=""):
    print(("PASS" if cond else "FAIL"), "-", name, ("" if cond else f":: {detail}"))
    if not cond:
        failures.append(name)


def run(script, args=None, cwd=None):
    return subprocess.run([sys.executable, str(script)] + (args or []),
                          cwd=cwd, capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as d:
        c = Path(d) / "content" / "REFERENCE"
        c.mkdir(parents=True)
        (Path(d) / "content" / "_indexes").mkdir()
        (c / "Alpha.md").write_text(NOTE_A, encoding="utf-8")
        (c / "Beta.md").write_text(NOTE_B, encoding="utf-8")

        r = run(BUILD, cwd=d)
        check("build_indexes runs", r.returncode == 0, r.stderr)
        check("build_indexes notes=2", "notes=2" in r.stdout, r.stdout)

        r = run(LINT_SCAN, cwd=d)
        scan = json.loads(r.stdout)
        check("lint_scan no missing_frontmatter", scan["counts"]["missing_frontmatter"] == 0)
        check("lint_scan no bad_type", scan["counts"]["bad_type"] == 0)

        r = run(LINT_LINKS, cwd=d)
        links = json.loads(r.stdout)
        check("lint_links skips code span (no broken)", links["broken"] == {}, links["broken"])

        r = run(GAPS, cwd=d)
        check("gaps runs", r.returncode == 0, r.stderr)

        r = run(REFACTOR, ["rename", "--old", "Beta", "--new", "Gamma"], cwd=d)
        check("refactor rename ok", r.returncode == 0, r.stderr)
        alpha = (c / "Alpha.md").read_text(encoding="utf-8")
        check("refactor rewrote link", "[[Gamma]]" in alpha and "[[Beta]]" not in alpha)
        check("refactor renamed file", (c / "Gamma.md").exists())

    print("---")
    if failures:
        print("FAILURES:", failures)
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
