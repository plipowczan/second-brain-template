#!/usr/bin/env python3
"""Integration self-tests for the KB template skills. Builds a throwaway temp vault
and exercises build_indexes, lint_scan, lint_links, gaps, and refactor end to end, then
adopts and upgrades a synthetic old base with brain-upgrade, and runs the curate and
brain-upgrade unit suites.
Run from anywhere:  python tests/run_tests.py   (exit 0 = all pass)."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / ".claude" / "skills"
BUILD = SKILLS / "brain-reindex" / "scripts" / "build_indexes.py"
LINT_SCAN = SKILLS / "brain-lint" / "scripts" / "lint_scan.py"
LINT_LINKS = SKILLS / "brain-lint" / "scripts" / "lint_links.py"
REFACTOR = SKILLS / "brain-refactor" / "scripts" / "refactor.py"
GAPS = SKILLS / "brain-gaps" / "scripts" / "gaps.py"
CURATE_SCRIPTS = SKILLS / "brain-curate" / "scripts"
UPGRADE_SCRIPTS = SKILLS / "brain-upgrade" / "scripts"
UPGRADE = UPGRADE_SCRIPTS / "upgrade.py"
DEV = ROOT / "dev"

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


def adoption_case():
    """brain-upgrade end to end: a synthetic pre-0.1.0 base (old skill paths, no
    CHANGELOG.md) is adopted to the older release 0.1.0 and then upgraded to 0.2.0, with
    the template's git clone as the source (no network)."""
    sys.path.insert(0, str(UPGRADE_SCRIPTS))
    import fixtures as fx
    import kbtemplate as kt

    with tempfile.TemporaryDirectory() as d:
        repo, base = Path(d) / "template", Path(d) / "kb"
        shas = fx.build_history(repo)
        tree = {p: v for p, v in fx.enc(fx.P0).items() if not p.endswith(".template.md")}
        tree[".claude/hooks/hook.py"] = fx.P2[".claude/hooks/hook.py"].encode()  # re-pulled
        tree["AGENTS.md"] = b"# Test KB\n\nOwner: Owner\n"
        tree[kt.ONBOARD_VALUES] = json.dumps(fx.VALUES).encode()
        fx.write_tree(base, tree)
        fx.git_init(base)
        fx.git(base, "add", "-A")
        fx.git(base, "commit", "-q", "-m", "my base")
        seeded = {p: kt.file_hash(base / p) for p in ("README.md", "content/REFERENCE/Example.md")}
        decisions = Path(d) / "decisions.json"
        decisions.write_text("{}", encoding="utf-8")

        def cycle(name, *extra):
            plan = str(Path(d) / f"{name}.json")
            steps = [["plan", "--instance", str(base), "--source", str(repo), "--out", plan, *extra],
                     ["apply", "--plan", plan, "--decisions", str(decisions)],
                     ["commit", "--plan", plan]]
            for args in steps:
                r = run(UPGRADE, args)
                check(f"brain-upgrade {name}: {args[0]}", r.returncode == 0, r.stdout + r.stderr)
            return json.loads(Path(plan).read_text(encoding="utf-8"))

        adopt = cycle("adopt", "--adopt")
        check("adoption picks release 0.1.0", adopt["to_version"] == "0.1.0", adopt["to_version"])
        stamp = json.loads(fx.git(base, "show", f"HEAD:{kt.STAMP}"))
        check("adoption stamp names 0.1.0 and its commit",
              (stamp["version"], stamp["commit"]) == ("0.1.0", shas["P1"]), stamp["version"])
        check("re-pulled newer file not rewound",
              (base / ".claude/hooks/hook.py").read_text(encoding="utf-8") == "hook v2\n")
        check("pristine old file moved to 0.1.0",
              (base / ".claude/skills/ingest/SKILL.md").read_text(encoding="utf-8") == "ingest v1\n")

        upgrade = cycle("upgrade")
        log = fx.git(base, "log", "--format=%s").splitlines()
        check("two commits: adoption, then upgrade",
              log[:3] == [f"chore(template): upgrade to {fx.REPO} 0.2.0",
                          f"chore(template): adopt {fx.REPO} 0.1.0", "my base"], log[:3])
        stamp = json.loads((base / kt.STAMP).read_text(encoding="utf-8"))
        check("upgrade stamp names 0.2.0", stamp["version"] == "0.2.0", stamp["version"])
        check("pre-rename skill deleted in the upgrade",
              any(a["path"] == ".claude/skills/ingest/SKILL.md" and a["kind"] == "delete"
                  for a in upgrade["actions"]) and not (base / ".claude/skills/ingest").exists())
        check("content/ and README.md untouched",
              all(kt.file_hash(base / p) == h for p, h in seeded.items()))
        check("nothing left uncommitted", fx.git(base, "status", "--porcelain") == "")


def main():
    with tempfile.TemporaryDirectory() as d:
        c = Path(d) / "content" / "REFERENCE"
        c.mkdir(parents=True)
        (Path(d) / "content" / "_indexes").mkdir()
        (c / "Alpha.md").write_text(NOTE_A, encoding="utf-8")
        (c / "Beta.md").write_text(NOTE_B, encoding="utf-8")
        # A retired note in _graveyard/ must be excluded from indexing (curate skill).
        grave = Path(d) / "content" / "_graveyard"
        grave.mkdir()
        (grave / "Retired.md").write_text(NOTE_A.replace("Alpha", "Retired"), encoding="utf-8")

        r = run(BUILD, cwd=d)
        check("build_indexes runs", r.returncode == 0, r.stderr)
        check("build_indexes notes=2 (_graveyard excluded)", "notes=2" in r.stdout, r.stdout)

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

    adoption_case()

    # curate skill: run its pure-function unit suites (scoring + link classification).
    r = subprocess.run([sys.executable, "-m", "unittest", "-v"],
                       cwd=str(CURATE_SCRIPTS), capture_output=True, text=True)
    check("curate unit tests pass", r.returncode == 0, r.stderr)

    # brain-upgrade: sources, planner, apply/commit, adoption (no network needed).
    r = subprocess.run([sys.executable, "-m", "unittest"],
                       cwd=str(UPGRADE_SCRIPTS), capture_output=True, text=True)
    check("brain-upgrade unit tests pass", r.returncode == 0, r.stderr[-3000:])

    # Template source only: dev/ (author class) never reaches an instance, and its
    # check of every tracked file would fail there.
    if DEV.is_dir():
        r = run(DEV / "check_manifest.py", cwd=str(ROOT))
        check("dev/check_manifest.py passes", r.returncode == 0, r.stdout + r.stderr)
        r = subprocess.run([sys.executable, "-m", "unittest", "-v"],
                           cwd=str(DEV), capture_output=True, text=True)
        check("dev unit tests pass", r.returncode == 0, r.stderr)
    else:
        print("SKIP - dev/check_manifest.py (no dev/: not the template source)")

    print("---")
    if failures:
        print("FAILURES:", failures)
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
