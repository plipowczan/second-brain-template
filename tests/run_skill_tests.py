#!/usr/bin/env python3
"""Unit tests of every skill. Each `.claude/skills/<skill>/scripts/` directory with
`test_*.py` files is one suite, run in its own process from that directory (as
`python -m unittest` there would). tests/run_tests.py is the integration suite; this
runs the per-skill suites it does not.

A skipped test is not a pass: every skip is listed with its reason at the end, and in
the job summary and as a notice when run in GitHub Actions. A suite that finds no tests
fails. Run from anywhere:  python tests/run_skill_tests.py   (exit 0 = all pass)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"


def run_one_suite(suite_dir, report_path):
    """Child process: run one suite, write what ran and what was skipped as JSON."""
    os.chdir(suite_dir)
    sys.path[0] = str(suite_dir)
    tests = unittest.defaultTestLoader.discover(str(suite_dir), pattern="test_*.py",
                                                top_level_dir=str(suite_dir))
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(tests)
    report = {"ran": result.testsRun, "ok": result.wasSuccessful(),
              "skipped": [[t.id(), reason] for t, reason in result.skipped]}
    Path(report_path).write_text(json.dumps(report), encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) == 4 and sys.argv[1] == "--suite":
        return run_one_suite(Path(sys.argv[2]), sys.argv[3])

    suites = sorted({p.parent for p in SKILLS.glob("*/scripts/test_*.py")})
    if not suites:
        print(f"FAIL - no skill test suites found under {SKILLS}")
        return 1

    rows, skips, failed = [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        for i, suite in enumerate(suites):
            skill = suite.parent.name
            print(f"=== {skill} ({suite.relative_to(ROOT).as_posix()})", flush=True)
            report_path = Path(tmp) / f"{i}.json"
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--suite",
                            str(suite), str(report_path)])
            if not report_path.exists():
                rows.append((skill, 0, 0, "FAIL (suite crashed)"))
                failed.append(skill)
                continue
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if not report["ok"]:
                status = "FAIL"
            elif report["ran"] == 0:
                status = "FAIL (no tests found)"
            else:
                status = "PASS"
            if status != "PASS":
                failed.append(skill)
            rows.append((skill, report["ran"], len(report["skipped"]), status))
            skips += [(skill, test, reason) for test, reason in report["skipped"]]

    print("---")
    for skill, ran, skipped, status in rows:
        print(f"{status} - {skill}: {ran} run, {skipped} skipped")
    if skips:
        print(f"SKIPPED - {len(skips)} test(s) did not run, so they checked nothing:")
        for skill, test, reason in skips:
            print(f"  {skill}: {test} -- {reason}")
    print("---")
    print(f"FAILED: {', '.join(failed)}" if failed
          else f"ALL PASS ({len(skips)} skipped)" if skips else "ALL PASS")

    if os.environ.get("GITHUB_ACTIONS") == "true":
        report_to_github(rows, skips)
    return 1 if failed else 0


def report_to_github(rows, skips):
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        lines = ["## Skill unit tests", "", "| Skill | Run | Skipped | Result |",
                 "|---|---:|---:|---|"]
        lines += [f"| `{skill}` | {ran} | {skipped} | {status} |"
                  for skill, ran, skipped, status in rows]
        if skips:
            lines += ["", "**Skipped, so not checked by this run:**", ""]
            lines += [f"- `{skill}`: `{test}`: {reason}" for skill, test, reason in skips]
        with open(summary, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    for skill, test, reason in skips:
        print(f"::notice title=Skipped test ({skill})::{test}: {reason}")


if __name__ == "__main__":
    raise SystemExit(main())
