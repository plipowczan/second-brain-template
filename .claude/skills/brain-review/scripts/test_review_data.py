"""Tests for review_data.py. Run: python -m unittest test_review_data (from this folder).

The sibling scripts (oplog, lint_scan, metrics, inbox_order) are replaced by small fakes
that print fixed JSON, so each part is tested on its own; one test at the end runs the
real scripts on a small vault. Invented names only."""

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import review_data as rd  # noqa: E402

TODAY = dt.date(2026, 11, 27)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


def fake(folder: Path, name: str, output, code: int = 0) -> Path:
    """A script that records its arguments in <name>.calls and prints `output` as JSON."""
    calls = folder / f"{name}.calls"
    body = (
        "import json, sys\n"
        f"open({str(calls)!r}, 'a', encoding='utf-8').write(json.dumps(sys.argv[1:]) + '\\n')\n"
        f"sys.stdout.write({json.dumps(output)!r})\n"
        + (f"sys.stderr.write('boom\\n')\nsys.exit({code})\n" if code else "")
    )
    return write(folder / f"{name}.py", body)


def calls(folder: Path, name: str) -> list:
    path = folder / f"{name}.calls"
    if not path.is_file():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()]


def row(time, op, counts=None, notes=None):
    return {"time": time, "op": op, "counts": counts or {}, "notes": notes or [], "more": 0}


SCAN = {"total": 12, "issues": {"contradiction": ["content/T/Claim.md (2 markers)",
                                                  "content/Other.md (1 marker)"]}}
METRICS = {"snapshot": {"date": "2026-11-27", "notes": 12, "orphans": 2},
           "previous": None, "older": None, "callouts": [],
           "comparable": {"previous": True, "older": True},
           "lists": {"orphans": ["T/Lonely", "U/Far"], "isolated": ["T/Lonely"],
                     "weak": ["T/Thin"], "untouched_90d": []},
           "recorded": True}
INBOX = {"sources": [{"path": "content/_raw/inbox/a.md", "duplicate_of": None},
                     {"path": "content/_raw/inbox/b.md",
                      "duplicate_of": "content/_raw/processed/b.md"}],
         "attachments": [], "unusable": [{"path": "content/_raw/inbox/e.md",
                                          "reason": "empty"}],
         "take": [], "remaining": 0}


class Vault(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "vault"
        (self.root / "content").mkdir(parents=True)
        self.fakes = Path(self.tmp.name) / "fakes"
        self.fakes.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def scripts(self, rows=(), scan=SCAN, metrics=METRICS, inbox=INBOX):
        return {"oplog": fake(self.fakes, "oplog", list(rows)),
                "lint_scan": fake(self.fakes, "lint_scan", scan),
                "metrics": fake(self.fakes, "metrics", metrics),
                "inbox_order": fake(self.fakes, "inbox_order", inbox)}

    def gather(self, rows=(), scan=SCAN, metrics=METRICS, inbox=INBOX, scripts=None, **kw):
        scripts = scripts or self.scripts(rows, scan, metrics, inbox)
        return rd.gather(self.root, TODAY, scripts=scripts, **kw)


class TestPeriod(Vault):
    def test_default_is_seven_days(self):
        p = self.gather()["period"]
        self.assertEqual((p["since"], p["until"], p["days"], p["basis"]),
                         ("2026-11-20", "2026-11-27", 7, "default"))

    def test_starts_at_the_last_review_row(self):
        rows = [row("2026-11-10 09:00", "review", {"days": 7}),
                row("2026-11-24 08:00", "ingest", {"sources": 1}),
                row("2026-11-24 10:00", "review", {"days": 14}),
                row("2026-11-24 11:00", "ingest", {"sources": 2})]
        data = self.gather(rows=rows)
        self.assertEqual(data["period"]["since"], "2026-11-24")
        self.assertEqual(data["period"]["days"], 3)
        self.assertEqual(data["period"]["after"], "2026-11-24 10:00")
        # the ingest before that review belongs to the review before
        self.assertEqual(data["log"]["by_op"], {"ingest": {"runs": 1,
                                                           "counts": {"sources": 2}}})

    def test_a_row_in_the_minute_of_the_last_review_after_it_counts(self):
        # Times have minutes only: an ingest logged in the review's minute, after its row,
        # was not covered by that review; one logged before it was.
        rows = [row("2026-11-24 10:00", "ingest", {"sources": 1}),
                row("2026-11-24 10:00", "review", {"days": 7}),
                row("2026-11-24 10:00", "ingest", {"sources": 4}, ["Z/Late"])]
        data = self.gather(rows=rows)
        self.assertEqual(data["period"]["after"], "2026-11-24 10:00")
        self.assertEqual(data["log"]["by_op"], {"ingest": {"runs": 1,
                                                           "counts": {"sources": 4}}})
        self.assertEqual(data["log"]["folders"], [{"folder": "Z", "count": 1}])

    def test_same_day_review_covers_its_period_again(self):
        rows = [row("2026-11-27 07:00", "review", {"days": 5}),
                row("2026-11-23 07:00", "compile", {"created": 1})]
        p = self.gather(rows=rows)["period"]
        self.assertEqual((p["since"], p["days"], p["basis"]),
                         ("2026-11-22", 5, "last review, today"))

    def test_report_file_when_the_log_has_no_review(self):
        reports = self.root / "content" / "_outputs" / "reports"
        write(reports / "2026-11-15_review.md", "x")
        write(reports / "2026-11-18_review-2.md", "x")
        write(reports / "2026-11-27_review.md", "x")  # today: not a start
        write(reports / "2026-11-26_health-report.md", "x")
        p = self.gather()["period"]
        self.assertEqual((p["since"], p["basis"]), ("2026-11-18", "last report"))

    def test_since_and_days_override(self):
        rows = [row("2026-11-24 10:00", "review", {"days": 7})]
        p = self.gather(rows=rows, since=dt.date(2026, 11, 1))["period"]
        self.assertEqual((p["since"], p["days"], p["basis"]), ("2026-11-01", 26, "since"))
        p = self.gather(rows=rows, days=3)["period"]
        self.assertEqual((p["since"], p["basis"]), ("2026-11-24", "days"))


class TestParts(Vault):
    def test_log_grouped_sorted_and_folders(self):
        rows = [row("2026-11-26 10:00", "ingest", {"sources": 2, "created": 1},
                    ["AI/Agents/One", "AI/Agents/Two", "_raw/processed/x.md"]),
                row("2026-11-21 10:00", "ingest", {"sources": 1}, ["AI/Tools/Three"]),
                row("2026-11-22 10:00", "enhance", {"updated": 1}, ["Root", "[private]"]),
                row("2026-11-10 10:00", "ingest", {"sources": 9}, ["Old/Note"])]
        log = self.gather(rows=rows)["log"]
        self.assertEqual([r["time"] for r in log["rows"]],
                         ["2026-11-21 10:00", "2026-11-22 10:00", "2026-11-26 10:00"])
        self.assertEqual(log["by_op"]["ingest"], {"runs": 2,
                                                  "counts": {"sources": 3, "created": 1}})
        self.assertEqual(log["folders"], [{"folder": "AI/Agents", "count": 2},
                                          {"folder": "(root)", "count": 1},
                                          {"folder": "AI/Tools", "count": 1}])

    def test_recent_changes_in_the_period(self):
        write(self.root / "content" / "_indexes" / "vault-map.md",
              "# Vault Map\n\n## Folders\n- 2026-11-25 not a change\n\n## Recent Changes\n"
              "- 2026-11-26 T/New (a new note)\n- 2026-11-01 T/Old (an old one)\n"
              "free text\n")
        self.assertEqual(self.gather()["recent_changes"],
                         [{"date": "2026-11-26", "text": "T/New (a new note)"}])

    def test_answers_and_learning_in_the_period(self):
        out = self.root / "content" / "_outputs"
        write(out / "answers" / "2026-11-25_cake.md",
              "---\ntitle: \"How to bake: the basics\"\ndate: 2026-11-25\ngaps: 2\n---\n")
        write(out / "answers" / "2026-10-01_old.md", "---\ndate: 2026-10-01\ngaps: 1\n---\n")
        write(out / "answers" / "2026-11-24_nofm.md", "no frontmatter\n")
        write(out / "learning" / "2026-11-26_bread.md",
              "---\ntitle: 'Quiz: bread'\ndate: 2026-11-26\nmode: quiz  # or explain\n"
              "score: \"3.5/5\"\ngaps: 3\nmissed: 1\n---\n")
        data = self.gather()
        self.assertEqual([(a["title"], a["gaps"]) for a in data["answers"]],
                         [("How to bake: the basics", 2), ("2026-11-24_nofm", None)])
        self.assertEqual(data["learning"],
                         [{"path": "content/_outputs/learning/2026-11-26_bread.md",
                           "date": "2026-11-26", "title": "Quiz: bread", "gaps": 3,
                           "mode": "quiz", "score": "3.5/5", "missed": 1}])

    def test_contradictions_inbox_and_thin(self):
        rows = [row("2026-11-26 10:00", "ingest", {}, ["T/Something"])]
        data = self.gather(rows=rows)
        self.assertEqual(data["contradictions"], [{"note": "T/Claim", "count": 2},
                                                  {"note": "Other", "count": 1}])
        self.assertEqual(data["inbox"], {"sources": 2, "unusable": 1, "duplicates": 1,
                                         "files_only": False})
        self.assertEqual(data["thin"]["in_touched_folders"],
                         [{"note": "T/Lonely", "kinds": ["orphans", "isolated"]},
                          {"note": "T/Thin", "kinds": ["weak"]}])

    def test_thin_notes_come_from_the_folders_metrics_picked(self):
        # metrics.py cuts its lists to 20; the touched folders go to it with --folder, so
        # it picks their notes before the cut.
        rows = [row("2026-11-26 10:00", "ingest", {}, ["Z/Something"])]
        metrics = {**METRICS, "in_folders": {"orphans": ["Z/Late"], "isolated": [],
                                             "weak": ["Z/Late"]}}
        data = self.gather(rows=rows, metrics=metrics)
        self.assertEqual(data["thin"]["in_touched_folders"],
                         [{"note": "Z/Late", "kinds": ["orphans", "weak"]}])
        self.assertNotIn("in_folders", data["metrics"])
        self.assertEqual(calls(self.fakes, "metrics"),
                         [["--record", "--today", "2026-11-27", "--folder", "Z"]])

    def test_report_path_never_taken(self):
        reports = self.root / "content" / "_outputs" / "reports"
        self.assertEqual(self.gather()["report_path"],
                         "content/_outputs/reports/2026-11-27_review.md")
        write(reports / "2026-11-27_review.md", "x")
        write(reports / "2026-11-27_review-2.md", "x")
        self.assertEqual(self.gather()["report_path"],
                         "content/_outputs/reports/2026-11-27_review-3.md")


class TestScripts(Vault):
    def test_metrics_recorded_only_with_ten_notes(self):
        self.gather()
        self.assertEqual(calls(self.fakes, "metrics"), [["--record", "--today", "2026-11-27"]])

    def test_too_young_records_nothing(self):
        data = self.gather(scan={"total": 9, "issues": {}})
        self.assertTrue(data["too_young"])
        self.assertEqual(data["notes"], 9)
        self.assertIsNone(data["metrics"])
        self.assertEqual(calls(self.fakes, "metrics"), [])

    def test_without_lint_scan_metrics_counts_first(self):
        scripts = self.scripts()
        scripts["lint_scan"] = self.fakes / "gone.py"
        data = self.gather(scripts=scripts)
        self.assertEqual(data["notes"], 12)
        self.assertIsNone(data["contradictions"])
        self.assertEqual(calls(self.fakes, "metrics"),
                         [["--today", "2026-11-27"], ["--record", "--today", "2026-11-27"]])
        self.assertEqual([u["part"] for u in data["unavailable"]], ["contradictions"])

    def test_missing_scripts_are_unavailable_and_the_rest_is_gathered(self):
        gone = {k: self.fakes / f"gone-{k}.py" for k in rd.SCRIPTS}
        write(self.root / "content" / "_raw" / "inbox" / "a.md", "x")
        write(self.root / "content" / "_raw" / "inbox" / ".gitkeep", "")
        write(self.root / "content" / "_outputs" / "answers" / "2026-11-26_q.md",
              "---\ndate: 2026-11-26\ngaps: 1\n---\n")
        data = rd.gather(self.root, TODAY, scripts=gone)
        self.assertEqual(sorted(u["part"] for u in data["unavailable"]),
                         ["contradictions", "inbox", "log", "metrics"])
        self.assertTrue(all("is missing" in u["reason"] for u in data["unavailable"]))
        self.assertIsNone(data["notes"])
        self.assertFalse(data["too_young"])
        self.assertIsNone(data["metrics"])
        self.assertEqual(data["inbox"], {"sources": 1, "unusable": None, "duplicates": None,
                                         "files_only": True})
        self.assertEqual(len(data["answers"]), 1)
        self.assertEqual(data["period"]["basis"], "default")

    def test_failing_script_is_unavailable(self):
        scripts = self.scripts()
        scripts["inbox_order"] = fake(self.fakes, "broken", {}, code=3)
        data = self.gather(scripts=scripts)
        [entry] = data["unavailable"]
        self.assertEqual(entry["part"], "inbox")
        self.assertIn("exit 3", entry["reason"])
        self.assertIn("boom", entry["reason"])


def git(cwd, *args, date=None):
    env = dict(os.environ)
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=env)


class TestGit(Vault):
    def test_no_git(self):
        self.assertFalse(self.gather()["git"]["available"])

    def test_commits_in_the_period_and_uncommitted(self):
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "test@example.com")
        git(self.root, "config", "user.name", "Test")
        git(self.root, "config", "core.autocrlf", "false")
        content = self.root / "content"
        write(content / "T" / "Old.md", "old\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "old", date="2026-11-01T10:00:00Z")
        write(content / "T" / "Zażółć.md", "new\n")
        write(content / "T" / "Old.md", "changed\n")
        write(content / "_outputs" / "log.md", "| x |\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "new", date="2026-11-25T10:00:00Z")
        write(content / "U" / "Pending.md", "pending\n")
        write(content / "T" / "Old.md", "changed again\n")
        g = self.gather()["git"]
        self.assertTrue(g["available"])
        self.assertEqual(g["commits"], 1)
        self.assertEqual(g["created"], ["T/Zażółć"])
        self.assertEqual(g["changed"], ["T/Old", "T/Zażółć"])
        self.assertEqual(g["uncommitted"], ["T/Old", "U/Pending"])
        self.assertEqual(g["folders"], [{"folder": "T", "count": 2}])

    def test_commits_before_the_last_review_are_left_out(self):
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "test@example.com")
        git(self.root, "config", "user.name", "Test")
        content = self.root / "content"
        write(content / "T" / "Before.md", "x\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "before", date="2026-11-24T09:00:00Z")
        write(content / "T" / "After.md", "y\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "after", date="2026-11-24T11:00:00Z")
        rows = [row("2026-11-24 10:00", "review", {"days": 7})]
        g = self.gather(rows=rows)["git"]
        self.assertEqual((g["commits"], g["created"]), (1, ["T/After"]))

    def test_subfolder_of_a_repository_is_not_git_here(self):
        git(self.root.parent, "init", "-q")
        g = self.gather()["git"]
        self.assertFalse(g["available"])


class TestMain(unittest.TestCase):
    def run_main(self, *args, cwd):
        return subprocess.run([sys.executable, str(HERE / "review_data.py"), *args], cwd=cwd,
                              capture_output=True, text=True, encoding="utf-8")

    def test_bad_arguments(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "content").mkdir()
            for args in (["--since", "2026-13-01"], ["--since", "2026-11-27x"],
                         ["--since", "2026-11-01", "--days", "3"], ["--days", "0"],
                         ["--since", "2999-01-01"]):
                with self.subTest(args):
                    self.assertEqual(self.run_main(*args, cwd=d).returncode, 2)

    def test_no_content_folder(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_main(cwd=d)
            self.assertEqual(r.returncode, 2)
            self.assertIn("content/", r.stderr)


REAL = all(p.is_file() for p in rd.SCRIPTS.values())


@unittest.skipUnless(REAL, "a sibling script of review_data.py is missing")
class TestWithRealScripts(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            content = root / "content"
            names = [f"Note {i}" for i in range(12)]
            for i, name in enumerate(names):
                link = f"[[{names[(i + 1) % 11]}]]" if i < 11 else ""
                callout = "> [!contradiction] A says one thing\n" if i == 3 else ""
                write(content / "T" / f"{name}.md",
                      f"---\ntitle: {name}\ndate: 2026-11-20\ntags: [t]\n"
                      f"type: knowledge-note\nsummary: s\n---\n# {name}\n{link}\n{callout}"
                      + "Body text long enough to not be a stub. " * 5 + "\n")
            write(content / "_raw" / "inbox" / "waiting.md", "# Waiting\nsome text\n")
            oplog = [sys.executable, str(rd.SCRIPTS["oplog"]), "append"]
            subprocess.run(oplog + ["--op", "ingest", "--count", "sources=1",
                                    "--note", "T/Note 1", "--at", "2026-11-25T10:00"],
                           cwd=root, check=True, capture_output=True)
            r = subprocess.run([sys.executable, str(HERE / "review_data.py"),
                                "--today", "2026-11-27"], cwd=root, capture_output=True,
                               text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data["unavailable"], [])
            self.assertEqual(data["notes"], 12)
            self.assertFalse(data["too_young"])
            self.assertEqual(data["log"]["by_op"]["ingest"]["counts"], {"sources": 1})
            self.assertEqual(data["contradictions"], [{"note": "T/Note 3", "count": 1}])
            self.assertEqual(data["inbox"]["sources"], 1)
            self.assertTrue(data["metrics"]["recorded"])
            self.assertEqual(data["metrics"]["snapshot"]["notes"], 12)
            self.assertIn("T/Note 11", data["metrics"]["lists"]["orphans"])
            self.assertTrue((content / "_outputs" / "metrics.md").is_file())


if __name__ == "__main__":
    unittest.main()
