import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lint_links  # noqa: E402
import metrics  # noqa: E402
from test_lint_links import build_fixture  # noqa: E402

METRICS = HERE / "metrics.py"
LINT_LINKS = HERE / "lint_links.py"
TODAY = date(2026, 11, 27)
HAS_GIT = shutil.which("git") is not None

# Every metric on one vault, invented names: a main group A-B-C, two islands (D-E, F-G),
# a note without links (H), a note that links only to itself (S), links that count once
# (repeated, aliased, path-qualified), and links to files that are not notes.
GRAPH_VAULT = {
    "X/A.md": "[[B]] [[B|again]] [[X/B]] [[B#Part]] [[pic.png]] [[templates/T]] [[ATTACHMENTS/f.pdf]]\n",
    "X/B.md": "[[A]] [[C]]\n",
    "X/C.md": "[[A]]\n```\n[[H]]\n```\n`[[F]]`\n",
    "Y/D.md": "[[E]]\n",
    "Y/E.md": "nothing\n",
    "Z/F.md": "[[G]]\n",
    "Z/G.md": "[[F]] [[Missing]]\n",
    "H.md": "no links at all\n",
    "S.md": "[[S]]\n",
}


def write_vault(root, files):
    content = Path(root) / "content"
    content.mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        path = content / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    return content


def fm(day=None, reviewed=None):
    lines = ["---", 'title: "N"']
    if day:
        lines.append(f"date: {day}")
    if reviewed:
        lines.append(f"agent-reviewed: {reviewed}")
    return "\n".join(lines + ["---", "# N", ""])


def run(cwd, *args, expect=0):
    r = subprocess.run([sys.executable, str(METRICS), *args], cwd=cwd, capture_output=True)
    out, err = r.stdout.decode("utf-8"), r.stderr.decode("utf-8", "replace")
    if r.returncode != expect:
        raise AssertionError(f"exit {r.returncode}: {err}")
    return json.loads(out) if expect == 0 else err


def tree(root):
    """Every file under root with its bytes and modification time."""
    found = {}
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            with open(p, "rb") as f:
                found[p] = (f.read(), os.stat(p).st_mtime_ns)
    return found


def git(root, *args, when=None):
    env = dict(os.environ)
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{when}T12:00:00+00:00"
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, env=env)
    if r.returncode != 0:
        raise AssertionError(r.stderr.decode("utf-8", "replace"))
    return r.stdout


def git_init(root):
    git(root, "init", "-q")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "commit.gpgsign", "false")
    git(root, "config", "core.autocrlf", "false")


def commit(root, when, message="c"):
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-verify", "-m", message, when=when)


def snap(notes=40, orphans=0, isolated=0, weak=0, lpn=2.0, islands=0, untouched=0,
         basis="git", day="2026-11-27"):
    return metrics.make_snapshot({
        "date": day, "basis": basis, "notes": notes, "orphans": orphans,
        "isolated": isolated, "weak": weak, "links_per_note": lpn, "islands": islands,
        "untouched_90d": untouched})


def row(day, notes=40, orphans=0, isolated=0, weak=0, lpn="2.00", islands=0, untouched=0,
        basis="frontmatter"):
    return f"| {day} | {basis} | {notes} | {orphans} | {isolated} | {weak} | {lpn} | {islands} | {untouched} |"


def metrics_file(rows, extra=""):
    return "\n".join(["# Vault metrics", ""] + metrics.TABLE_HEADER + rows) + "\n" + extra


class TestGraphMetrics(unittest.TestCase):
    def measure(self, files, today=TODAY, commit_dates=None):
        with tempfile.TemporaryDirectory() as d:
            content = write_vault(d, files)
            return metrics.measure(str(content), today, commit_dates)

    def test_every_metric_on_a_small_vault(self):
        s, lists = self.measure(GRAPH_VAULT)
        self.assertEqual(s["notes"], 9)
        self.assertEqual((s["orphans"], s["orphans_pct"]), (2, 22.2))
        self.assertEqual(lists["orphans"], ["H", "Y/D"])
        self.assertEqual((s["isolated"], s["isolated_pct"]), (2, 22.2))
        self.assertEqual(lists["isolated"], ["H", "S"])
        # D and E have one link each; A <-> B counts two for each (as in brain-gaps).
        self.assertEqual((s["weak"], s["weak_pct"]), (4, 44.4))
        self.assertEqual(lists["weak"], ["H", "S", "Y/D", "Y/E"])
        # A->B, B->A, B->C, C->A, D->E, F->G, G->F: 7 distinct links over 9 notes.
        self.assertEqual(s["links_per_note"], 0.78)
        self.assertEqual(s["islands"], 2)

    def test_self_link_is_isolated_and_weak_not_orphan(self):
        s, lists = self.measure({"S.md": "[[S]] [[s]]\n", "A.md": "[[B]]\n", "B.md": "[[A]]\n"})
        self.assertEqual(lists["orphans"], [])
        self.assertEqual(lists["isolated"], ["S"])
        self.assertEqual(lists["weak"], ["S"])
        self.assertEqual(s["links_per_note"], 0.67)

    def test_note_without_any_link(self):
        s, lists = self.measure({"H.md": "plain text\n", "A.md": "[[B]]\n", "B.md": "[[A]]\n"})
        for key in ("orphans", "isolated", "weak"):
            self.assertEqual(lists[key], ["H"], key)
        self.assertEqual(s["islands"], 0)

    def test_empty_vault_gives_nulls(self):
        s, lists = self.measure({})
        self.assertEqual(s["notes"], 0)
        for key in ("orphans_pct", "isolated_pct", "weak_pct", "links_per_note",
                    "untouched_90d_pct"):
            self.assertIsNone(s[key], key)
        self.assertEqual((s["orphans"], s["isolated"], s["weak"], s["islands"],
                          s["untouched_90d"], s["untouched_unknown"]), (0, 0, 0, 0, 0, 0))
        self.assertEqual(lists, {"orphans": [], "isolated": [], "weak": [], "untouched_90d": []})

    def test_case_insensitive_link_counts(self):
        s, lists = self.measure({"Hub.md": "[[leaf]]\n", "Leaf.md": "[[HUB]]\n"})
        self.assertEqual((s["orphans"], s["isolated"], s["links_per_note"]), (0, 0, 1.0))

    def test_files_sharing_a_name(self):
        # One [[Dup]] is one distinct link and reaches both files; a link between the two
        # files is a self-link; the name is one node, so the group is X + Dup, no island.
        s, lists = self.measure({"X.md": "[[Dup]]\n", "P/Dup.md": "[[Q/Dup]]\n",
                                 "Q/Dup.md": "text\n"})
        self.assertEqual(s["notes"], 3)
        self.assertEqual(s["links_per_note"], 0.33)
        self.assertEqual(lists["orphans"], ["X"])
        self.assertEqual(lists["isolated"], [])
        self.assertEqual(lists["weak"], ["P/Dup", "Q/Dup", "X"])
        self.assertEqual(s["islands"], 0)

    def test_two_unlinked_files_of_one_name_are_not_an_island(self):
        s, lists = self.measure({"A.md": "[[B]]\n", "B.md": "[[A]]\n",
                                 "P/Twin.md": "[[Twin]]\n", "Q/Twin.md": "[[Q/Twin]]\n"})
        self.assertEqual(s["islands"], 0)
        self.assertEqual(lists["isolated"], ["P/Twin", "Q/Twin"])

    def test_fixture_of_lint_links(self):
        with tempfile.TemporaryDirectory() as d:
            s, lists = metrics.measure(str(build_fixture(d)), TODAY)
        self.assertEqual((s["notes"], s["orphans"], s["isolated"], s["weak"], s["islands"]),
                         (9, 1, 3, 6, 0))
        self.assertEqual(s["links_per_note"], 0.67)
        self.assertEqual(lists["isolated"], ["A/Dup", "B/Dup", "T/Self"])

    def test_lists_are_capped_and_sorted(self):
        files = {f"N{i:02d}.md": "x\n" for i in range(25)}
        s, lists = self.measure(files)
        self.assertEqual(s["orphans"], 25)
        self.assertEqual(len(lists["orphans"]), 20)
        self.assertEqual(lists["orphans"], sorted(lists["orphans"]))
        self.assertEqual(lists["orphans"][0], "N00")

    def test_folder_lists_are_picked_before_the_cut(self):
        # A folder late in the alphabet must not vanish behind 20 notes of an earlier one.
        files = {f"A/N{i:02d}.md": "x\n" for i in range(25)}
        files["Z/Late.md"] = "x\n"
        files["Top.md"] = "x\n"
        with tempfile.TemporaryDirectory() as d:
            content = write_vault(d, files)
            s, lists = metrics.measure(str(content), TODAY, None, ["Z", "(root)"])
            out = run(d, "--today", TODAY.isoformat(), "--folder", "Z")
            plain = run(d, "--today", TODAY.isoformat())
        self.assertEqual(len(lists["orphans"]), 20)
        self.assertNotIn("Z/Late", lists["orphans"])
        self.assertEqual(lists["in_folders"],
                         {"orphans": ["Top", "Z/Late"], "isolated": ["Top", "Z/Late"],
                          "weak": ["Top", "Z/Late"]})
        self.assertEqual(out["in_folders"]["orphans"], ["Z/Late"])
        self.assertNotIn("in_folders", out["lists"])
        self.assertNotIn("in_folders", plain)


class TestSameOrphansAsLint(unittest.TestCase):
    def test_metrics_and_lint_links_agree_on_the_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d)
            lint = subprocess.run([sys.executable, str(LINT_LINKS)], cwd=d,
                                  capture_output=True)
            lint = json.loads(lint.stdout.decode("utf-8"))
            out = run(d, "--today", TODAY.isoformat())
        self.assertEqual(out["snapshot"]["orphans"], lint["orphan_count"])
        self.assertEqual(sorted(p.split("/")[-1] for p in out["lists"]["orphans"]),
                         lint["orphans"])

    def test_scan_edges_agree_with_incoming(self):
        with tempfile.TemporaryDirectory() as d:
            result = lint_links.scan(str(write_vault(d, GRAPH_VAULT)))
        self.assertEqual({t for _, t in result["edges"]}, result["incoming"])


class TestLastTouch(unittest.TestCase):
    def measure(self, files, commit_dates=None):
        with tempfile.TemporaryDirectory() as d:
            content = write_vault(d, files)
            return metrics.measure(str(content), TODAY, commit_dates)

    def test_frontmatter_date_and_agent_reviewed(self):
        old = "2026-01-01"
        recent = (TODAY - timedelta(days=10)).isoformat()
        s, lists = self.measure({
            "Old.md": fm(old),
            "Quoted.md": fm(f'"{old}"', reviewed=f'"{recent}"'),
            "Plain.md": fm(old, reviewed=recent),
            "Single.md": fm(f"'{recent}'"),
            "None.md": "# no frontmatter\n",
            "Bad.md": fm("2026-02-30"),
        })
        self.assertEqual(lists["untouched_90d"], ["Old"])
        self.assertEqual((s["untouched_90d"], s["untouched_unknown"]), (1, 2))
        self.assertEqual(s["untouched_90d_pct"], 16.7)

    def test_ninety_days_is_untouched_eighty_nine_is_not(self):
        s, lists = self.measure({
            "At.md": fm((TODAY - timedelta(days=90)).isoformat()),
            "Before.md": fm((TODAY - timedelta(days=89)).isoformat()),
        })
        self.assertEqual(lists["untouched_90d"], ["At"])

    def test_untouched_list_is_oldest_first(self):
        s, lists = self.measure({"B.md": fm("2025-06-01"), "A.md": fm("2026-01-01"),
                                 "C.md": fm("2025-06-01")})
        self.assertEqual(lists["untouched_90d"], ["B", "C", "A"])

    def test_commit_date_counts_in_a_git_basis(self):
        s, lists = self.measure({"T/Old.md": fm("2025-01-01"), "T/New.md": fm("2025-01-01"),
                                 "T/Bare.md": "# none\n"},
                                commit_dates={"T/New.md": TODAY - timedelta(days=3),
                                              "T/Bare.md": date(2025, 5, 1)})
        self.assertEqual(s["basis"], "git")
        self.assertEqual(lists["untouched_90d"], ["T/Old", "T/Bare"])
        self.assertEqual(s["untouched_unknown"], 0)


@unittest.skipUnless(HAS_GIT, "git is not installed")
class TestGitBasis(unittest.TestCase):
    FILES = {
        "T/Old.md": fm("2026-01-01"),
        "T/Fresh.md": fm("2026-01-01"),
        "T/Zażółć.md": fm("2025-01-01"),
        "T/NoDate.md": "# no date\n",
    }

    def build(self, d):
        write_vault(d, self.FILES)
        git_init(d)
        commit(d, "2026-01-05")
        Path(d, "content", "T", "Fresh.md").write_bytes(fm("2026-01-01").encode() + b"more\n")
        Path(d, "content", "T", "Zażółć.md").write_bytes(
            fm("2025-01-01").encode() + b"more\n")
        commit(d, "2026-11-01")
        Path(d, "content", "T", "Fresh.md").write_bytes(fm("2026-01-01").encode() + b"again\n")
        commit(d, "2026-11-20")
        # Not committed: no commit date, no frontmatter date.
        Path(d, "content", "T", "Untracked.md").write_bytes(b"# new\n")

    def test_git_basis_reads_commit_dates(self):
        with tempfile.TemporaryDirectory() as d:
            self.build(d)
            out = run(d, "--today", TODAY.isoformat())
        s = out["snapshot"]
        self.assertEqual(s["basis"], "git")
        # Zażółć.md was committed on 2026-11-01: found although its name is not ASCII.
        self.assertEqual(out["lists"]["untouched_90d"], ["T/NoDate", "T/Old"])
        self.assertEqual((s["untouched_90d"], s["untouched_unknown"]), (2, 1))

    def test_commit_days_takes_the_latest_commit(self):
        with tempfile.TemporaryDirectory() as d:
            self.build(d)
            cwd = os.getcwd()
            os.chdir(d)
            try:
                days = metrics.commit_days("content")
                basis = metrics.git_basis()
            finally:
                os.chdir(cwd)
        self.assertTrue(basis)
        self.assertEqual(days["T/Fresh.md"], date(2026, 11, 20))
        self.assertEqual(days["T/Zażółć.md"], date(2026, 11, 1))
        self.assertEqual(days["T/Old.md"], date(2026, 1, 5))
        self.assertNotIn("T/Untracked.md", days)

    def test_frontmatter_basis_without_git(self):
        with tempfile.TemporaryDirectory() as d:
            write_vault(d, self.FILES)
            out = run(d, "--today", TODAY.isoformat())
        s = out["snapshot"]
        self.assertEqual(s["basis"], "frontmatter")
        self.assertEqual(out["lists"]["untouched_90d"], ["T/Zażółć", "T/Fresh", "T/Old"])
        self.assertEqual((s["untouched_90d"], s["untouched_unknown"]), (3, 1))

    def test_repository_without_commits_is_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            write_vault(d, self.FILES)
            git_init(d)
            self.assertEqual(run(d, "--today", TODAY.isoformat())["snapshot"]["basis"],
                             "frontmatter")

    def test_vault_below_the_top_of_a_repository_is_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            vault = Path(d) / "vault"
            write_vault(vault, self.FILES)
            git_init(d)
            commit(d, "2026-11-20")
            self.assertEqual(run(vault, "--today", TODAY.isoformat())["snapshot"]["basis"],
                             "frontmatter")

    def test_shallow_clone_is_frontmatter(self):
        # History stops at the graft: every file would date from the one commit there.
        with tempfile.TemporaryDirectory() as d:
            origin, clone = Path(d) / "origin", Path(d) / "clone"
            self.build(origin)
            r = subprocess.run(["git", "clone", "-q", "--depth", "1", origin.as_uri(),
                                str(clone)], capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
            self.assertEqual(git(clone, "rev-parse", "--is-shallow-repository").strip(), b"true")
            out = run(clone, "--today", TODAY.isoformat())
        s = out["snapshot"]
        self.assertEqual(s["basis"], "frontmatter")
        self.assertEqual(out["lists"]["untouched_90d"], ["T/Zażółć", "T/Fresh", "T/Old"])

    def test_nothing_written_in_a_git_vault(self):
        with tempfile.TemporaryDirectory() as d:
            self.build(d)
            before = tree(d)
            run(d, "--today", TODAY.isoformat())
            self.assertEqual(tree(d), before)


class TestRecord(unittest.TestCase):
    def vault(self, d, n=3):
        write_vault(d, {f"N{i}.md": fm("2026-11-01") for i in range(n)})
        return Path(d) / "content" / "_outputs" / "metrics.md"

    def test_nothing_written_without_record(self):
        with tempfile.TemporaryDirectory() as d:
            self.vault(d)
            before = tree(d)
            out = run(d, "--today", TODAY.isoformat())
            self.assertEqual(tree(d), before)
        self.assertFalse(out["recorded"])

    def test_nothing_written_without_record_when_the_file_exists(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.vault(d)
            path.parent.mkdir(parents=True)
            path.write_bytes(metrics_file([row("2026-11-01", notes=3)]).encode())
            before = tree(d)
            run(d, "--today", TODAY.isoformat())
            self.assertEqual(tree(d), before)

    def test_record_creates_the_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.vault(d)
            out = run(d, "--record", "--today", TODAY.isoformat())
            data = path.read_bytes()
        self.assertTrue(out["recorded"])
        self.assertIsNone(out["previous"])
        self.assertNotIn(b"\r", data)
        self.assertEqual(data.decode("utf-8"), metrics_file(
            ["| 2026-11-27 | frontmatter | 3 | 3 | 3 | 3 | 0.00 | 0 | 0 |"]))

    def test_record_on_the_same_day_replaces_the_row(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.vault(d)
            run(d, "--record", "--today", "2026-11-20")
            run(d, "--record", "--today", TODAY.isoformat())
            Path(d, "content", "N9.md").write_bytes(b"[[N0]]\n")
            out = run(d, "--record", "--today", TODAY.isoformat())
            text = path.read_bytes().decode("utf-8")
        rows = [line for line in text.splitlines() if line.startswith("| 2026")]
        self.assertEqual(rows, [
            "| 2026-11-20 | frontmatter | 3 | 3 | 3 | 3 | 0.00 | 0 | 0 |",
            "| 2026-11-27 | frontmatter | 4 | 3 | 2 | 4 | 0.25 | 0 | 0 |"])
        self.assertEqual(out["previous"]["date"], "2026-11-20")

    def test_record_over_two_rows_of_one_date_leaves_one(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.vault(d)
            path.parent.mkdir(parents=True)
            path.write_bytes(metrics_file(
                [row(TODAY.isoformat(), notes=9), row("2026-11-01", notes=5),
                 row(TODAY.isoformat(), notes=8)], extra="\nA note of mine.\n").encode())
            run(d, "--record", "--today", TODAY.isoformat())
            text = path.read_bytes().decode("utf-8")
        self.assertEqual(text, metrics_file(
            [row("2026-11-01", notes=5),
             "| 2026-11-27 | frontmatter | 3 | 3 | 3 | 3 | 0.00 | 0 | 0 |"],
            extra="\nA note of mine.\n"))

    def test_new_row_goes_after_the_table_and_keeps_other_lines(self):
        text = metrics_file([row("2026-11-01")], extra="\nWritten by hand.\n")
        new = metrics.recorded_text(text, snap(basis="frontmatter", day="2026-11-27"))
        self.assertEqual(new, metrics_file(
            [row("2026-11-01"), "| 2026-11-27 | frontmatter | 40 | 0 | 0 | 0 | 2.00 | 0 | 0 |"],
            extra="\nWritten by hand.\n"))

    def test_crlf_file_is_rewritten_with_lf(self):
        text = metrics_file([row("2026-11-01")]).replace("\n", "\r\n")
        new = metrics.recorded_text(text, snap(day="2026-11-27"))
        self.assertNotIn("\r", new)
        self.assertEqual(len(metrics.read_history(new)), 2)

    def test_empty_vault_row_round_trips(self):
        s = metrics.make_snapshot({"date": "2026-11-27", "basis": "git", "notes": 0,
                                   "orphans": 0, "isolated": 0, "weak": 0,
                                   "links_per_note": None, "islands": 0, "untouched_90d": 0})
        line = metrics.format_row(s)
        self.assertEqual(line, "| 2026-11-27 | git | 0 | 0 | 0 | 0 | - | 0 | 0 |")
        back = metrics.read_history(metrics.recorded_text(None, s))
        self.assertEqual(back, [dict(s, untouched_unknown=None)])


class TestHistory(unittest.TestCase):
    def test_last_row_per_date_wins(self):
        history = metrics.read_history(metrics_file(
            [row("2026-11-20", orphans=4), row("2026-11-20", orphans=9)]))
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["orphans"], 9)

    def test_rows_out_of_order_are_sorted(self):
        history = metrics.read_history(metrics_file(
            [row("2026-11-20"), row("2026-10-01"), row("2026-11-25")]))
        self.assertEqual([s["date"] for s in history], ["2026-10-01", "2026-11-20", "2026-11-25"])

    def test_invalid_lines_are_skipped(self):
        text = metrics_file([
            row("2026-11-20"),
            "| 2026-11-21 | git | 40 | 0 | 0 | 0 | 2.00 | 0 |",       # 8 cells
            row("2026-11-22", basis="svn"),
            row("2026-02-30"),
            row("2026-11-23", orphans=41),                            # more than notes
            row("2026-11-24", lpn="many"),
            row("2026-11-25", lpn="-"),                               # null with notes
            "2026-11-26 | git | 40 | 0 | 0 | 0 | 2.00 | 0 | 0",       # no pipes at the ends
            "Some text | with pipes |",
        ])
        self.assertEqual([s["date"] for s in metrics.read_history(text)], ["2026-11-20"])

    def test_row_snapshot_has_shares_and_null_unknown(self):
        s = metrics.read_history(metrics_file(
            [row("2026-11-20", notes=40, orphans=4, isolated=2, weak=10, lpn="1.25",
                 islands=3, untouched=8, basis="git")]))[0]
        self.assertEqual(s, {
            "date": "2026-11-20", "basis": "git", "notes": 40, "orphans": 4,
            "orphans_pct": 10.0, "isolated": 2, "isolated_pct": 5.0, "weak": 10,
            "weak_pct": 25.0, "links_per_note": 1.25, "islands": 3, "untouched_90d": 8,
            "untouched_90d_pct": 20.0, "untouched_unknown": None})

    def test_previous_and_older(self):
        history = metrics.read_history(metrics_file([
            row("2026-11-27"), row("2026-12-01"), row("2026-11-20"), row("2026-10-31"),
            row("2026-10-30"), row("2026-09-01")]))
        previous, older = metrics.pick_earlier(history, TODAY)
        self.assertEqual(previous["date"], "2026-11-20")
        self.assertEqual(older["date"], "2026-10-30")   # 28 days; 10-31 is only 27

    def test_no_history(self):
        self.assertEqual(metrics.pick_earlier([], TODAY), (None, None))
        self.assertEqual(metrics.read_history(None), [])

    def test_previous_can_also_be_older(self):
        history = metrics.read_history(metrics_file([row("2026-09-01")]))
        previous, older = metrics.pick_earlier(history, TODAY)
        self.assertEqual(previous["date"], "2026-09-01")
        self.assertEqual(older["date"], "2026-09-01")


class TestCallouts(unittest.TestCase):
    def names(self, current, earlier):
        return [c["metric"] for c in metrics.callouts(current, earlier, "previous")]

    def test_first_snapshot_calls_out_nothing(self):
        self.assertEqual(metrics.callouts(snap(orphans=30), None, "previous"), [])

    def test_one_new_orphan_in_a_40_note_base(self):
        self.assertEqual(self.names(snap(orphans=5), snap(orphans=4)), [])

    def test_two_new_orphans_in_a_40_note_base(self):
        found = metrics.callouts(snap(orphans=6), snap(orphans=4), "older")
        self.assertEqual(found, [{"metric": "orphans", "against": "older", "from": 4, "to": 6,
                                  "from_pct": 10.0, "to_pct": 15.0}])

    def test_share_step_is_two_points(self):
        self.assertEqual(self.names(snap(100, orphans=12), snap(100, orphans=10)), ["orphans"])
        self.assertEqual(self.names(snap(200, isolated=23), snap(200, isolated=20)), [])
        self.assertEqual(self.names(snap(100, isolated=12), snap(100, isolated=10)),
                         ["isolated"])

    def test_more_notes_can_hide_new_orphans(self):
        # 4 of 40 (10 %) to 6 of 60 (10 %): two more orphans, no worse a share.
        self.assertEqual(self.names(snap(60, orphans=6), snap(40, orphans=4)), [])

    def test_islands_step(self):
        self.assertEqual(self.names(snap(islands=2), snap(islands=1)), ["islands"])
        self.assertEqual(self.names(snap(islands=1), snap(islands=1)), [])

    def test_links_per_note_step(self):
        self.assertEqual(self.names(snap(lpn=1.8), snap(lpn=2.3)), ["links_per_note"])
        self.assertEqual(self.names(snap(lpn=1.81), snap(lpn=2.3)), [])
        self.assertEqual(self.names(snap(lpn=3.0), snap(lpn=2.0)), [])

    def test_untouched_step(self):
        self.assertEqual(self.names(snap(100, untouched=15), snap(100, untouched=10)),
                         ["untouched_90d"])
        self.assertEqual(self.names(snap(100, untouched=14), snap(100, untouched=10)), [])
        # 4 of 40 (10 %) to 5 of 30 (16.7 %): more than 5 points, but only one note more.
        self.assertEqual(self.names(snap(30, untouched=5), snap(40, untouched=4)), [])

    def test_untouched_not_compared_across_bases(self):
        current = snap(100, untouched=30, islands=2, basis="frontmatter")
        earlier = snap(100, untouched=10, islands=1, basis="git")
        self.assertEqual(self.names(current, earlier), ["islands"])
        self.assertFalse(metrics.comparable(current, earlier))
        self.assertTrue(metrics.comparable(current, snap(basis="frontmatter")))
        self.assertFalse(metrics.comparable(current, None))

    def test_below_30_notes_nothing(self):
        worse = dict(orphans=20, isolated=20, islands=5, lpn=0.1, untouched=20)
        self.assertEqual(self.names(snap(29, **worse), snap(29)), [])
        self.assertEqual(len(self.names(snap(30, **worse), snap(29))), 5)

    def test_earlier_without_notes(self):
        earlier = metrics.make_snapshot({
            "date": "2026-11-01", "basis": "git", "notes": 0, "orphans": 0, "isolated": 0,
            "weak": 0, "links_per_note": None, "islands": 0, "untouched_90d": 0})
        self.assertEqual(self.names(snap(40, orphans=10, islands=1), earlier), ["islands"])

    def test_improvement_is_not_called_out(self):
        self.assertEqual(self.names(snap(orphans=0, islands=0, lpn=3.0),
                                    snap(orphans=10, islands=3, lpn=1.0)), [])


class TestCommandLine(unittest.TestCase):
    def test_contract_keys(self):
        with tempfile.TemporaryDirectory() as d:
            write_vault(d, GRAPH_VAULT)
            out = run(d, "--today", TODAY.isoformat())
        self.assertEqual(list(out), ["snapshot", "previous", "older", "callouts", "comparable",
                                     "lists", "recorded"])
        self.assertEqual(list(out["snapshot"]), [
            "date", "basis", "notes", "orphans", "orphans_pct", "isolated", "isolated_pct",
            "weak", "weak_pct", "links_per_note", "islands", "untouched_90d",
            "untouched_90d_pct", "untouched_unknown"])
        self.assertEqual(out["comparable"], {"previous": False, "older": False})

    def test_callouts_against_previous_and_older(self):
        with tempfile.TemporaryDirectory() as d:
            write_vault(d, {f"N{i:02d}.md": fm("2026-11-01") for i in range(30)})
            path = Path(d, "content", "_outputs", "metrics.md")
            path.parent.mkdir(parents=True)
            path.write_bytes(metrics_file([
                row("2026-11-20", notes=30, orphans=30, isolated=30, weak=30, lpn="0.00"),
                row("2026-10-01", notes=30, orphans=0, isolated=0, weak=0, lpn="0.00"),
            ]).encode())
            out = run(d, "--today", TODAY.isoformat())
        self.assertEqual(out["previous"]["date"], "2026-11-20")
        self.assertEqual(out["older"]["date"], "2026-10-01")
        self.assertEqual(out["comparable"], {"previous": True, "older": True})
        self.assertEqual([(c["metric"], c["against"]) for c in out["callouts"]],
                         [("orphans", "older"), ("isolated", "older")])

    def test_not_comparable_across_bases(self):
        with tempfile.TemporaryDirectory() as d:
            write_vault(d, {f"N{i:02d}.md": fm("2025-01-01") for i in range(30)})
            path = Path(d, "content", "_outputs", "metrics.md")
            path.parent.mkdir(parents=True)
            path.write_bytes(metrics_file([
                row("2026-11-20", notes=30, orphans=30, isolated=30, weak=30, lpn="0.00",
                    untouched=0, basis="git")]).encode())
            out = run(d, "--today", TODAY.isoformat())
        self.assertEqual(out["snapshot"]["untouched_90d"], 30)
        self.assertEqual(out["comparable"], {"previous": False, "older": False})
        self.assertEqual(out["callouts"], [])

    def test_bad_today_and_missing_content(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("YYYY-MM-DD", run(d, "--today", "27.11.2026", expect=2))
            self.assertIn("content", run(d, expect=2))
            self.assertEqual(os.listdir(d), [])


if __name__ == "__main__":
    unittest.main()
