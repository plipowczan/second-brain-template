#!/usr/bin/env python3
"""The default path of brain-upgrade, run with the commands SKILL.md itself prescribes.

Every other suite calls the engine with arguments of its own, and most of them pass the
owner's consent. So a skill line that the engine refuses went unnoticed until the 0.2.1
pilot. Here the commands are read from SKILL.md, so a flag added to the default path, or
a default line the engine refuses, fails this suite. No test touches the network:
downloads go through a stub opener. Run: python -m unittest -v"""

import json
import re
import shlex
import unittest
from pathlib import Path

import fixtures as fx
import kbtemplate as kt
from test_planner import make_instance

SKILL = (Path(__file__).resolve().parent.parent / "SKILL.md").read_text(encoding="utf-8")
COMMIT = "a" * 40
FETCH = re.compile(r"`python \.claude/skills/brain-upgrade/scripts/upgrade\.py (fetch)"
                   r"(?: \[--to X\.Y\.Z\])?`")
ENGINE = re.compile(r"^python ENGINE (.+?)(?:\s+#.*)?$", re.M)


def phase(title: str) -> str:
    """One `## Phase N` section of SKILL.md."""
    m = re.search(rf"^## Phase \d+ — {re.escape(title)}.*?(?=^## )", SKILL, re.M | re.S)
    assert m, title
    return m.group(0)


def plan_lines() -> dict[str, str]:
    """The default dry-run lines of Phase 3, by their comment."""
    lines = re.findall(r"^python ENGINE (plan .+?)\s+# (\w+)$", phase("Plan"), re.M)
    return {name: cmd for cmd, name in lines}


class SkillPathCase(unittest.TestCase):
    def setUp(self):
        self.tmp = fx.TempDir()
        self.base = make_instance(self.tmp.path / "kb")
        self.archives: dict[str, bytes] = {}
        self.downloads: list[str] = []

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self, version: str, changes=None, comment: str = COMMIT) -> None:
        files = fx.template(version, {".claude/skills/brain-upgrade/scripts/upgrade.py": "# engine\n",
                                      **(changes or {})})
        self.archives[f"v{version}.zip"] = fx.zip_bytes(files, comment=comment)
        self.latest = version

    def opener(self, url: str) -> bytes:
        self.downloads.append(url)
        if url.endswith("/releases/latest"):
            return json.dumps({"tag_name": f"v{self.latest}"}).encode()
        return self.archives[url.rsplit("/", 1)[-1]]

    def skill_fetch(self) -> dict:
        self.assertTrue(FETCH.search(phase("The source")), "the fetch line left SKILL.md")
        code, out, err = fx.run("fetch", "--instance", str(self.base), opener=self.opener)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def run_line(self, line: str, **values) -> tuple[int, str, str]:
        """One command as SKILL.md writes it, with its capitals filled in."""
        for name, value in values.items():
            line = line.replace(name, value)
        line = line.replace("--instance .", f"--instance {self.base.as_posix()}")
        return fx.run(*shlex.split(line), opener=self.opener)

    def skill_plan(self, name: str, version: str) -> tuple[Path, str]:
        code, out, err = self.run_line(plan_lines()[name], VERSION=version)
        self.assertEqual(code, 0, err)
        return Path(re.search(r"^Plan: (.+)$", out, re.M).group(1)), out

    def skill_apply_and_commit(self, plan: Path) -> None:
        decisions = self.tmp.path / "decisions.json"
        decisions.write_text("{}", encoding="utf-8")
        lines = ENGINE.findall(phase("Apply")) + ENGINE.findall(phase("Commit and follow-up"))
        self.assertEqual([x.split()[0] for x in lines], ["apply", "commit"])
        for line in lines:
            code, out, err = self.run_line(line, PLAN=plan.as_posix(), DECISIONS=decisions.as_posix())
            self.assertEqual(code, 0, err)


class DefaultPathTest(SkillPathCase):
    def test_the_lines_of_the_skill_carry_no_consent(self):
        lines = plan_lines()
        self.assertEqual(sorted(lines), ["adoption", "upgrade"])
        for line in lines.values():
            self.assertNotIn("--allow-repository", line)
            self.assertNotIn("--source", line)

    def test_fetch_plan_apply_commit(self):
        self.publish("0.3.0", {".claude/hooks/hook.py": "print('hook v2')\n"})
        fetched = self.skill_fetch()
        self.assertTrue(fetched["provenance"]["verified"])
        self.assertTrue(fetched["engine_exists"])
        self.assertEqual(fetched["provenance"]["commit"], COMMIT)

        plan_file, summary = self.skill_plan("upgrade", fetched["provenance"]["version"])
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
        self.assertEqual(plan["source"]["kind"], "download")
        self.assertIn(f"commit {COMMIT}", summary)  # what Phase 3 compares with Phase 1

        self.skill_apply_and_commit(plan_file)
        stamp = json.loads(fx.git(self.base, "show", f"HEAD:{kt.STAMP}"))
        self.assertEqual((stamp["version"], stamp["commit"]), ("0.3.0", COMMIT))
        self.assertEqual((self.base / ".claude/hooks/hook.py").read_text(encoding="utf-8"),
                         "print('hook v2')\n")
        self.assertEqual(fx.git(self.base, "status", "--porcelain"), "")

    def test_the_plan_stays_on_the_version_the_owner_agreed_to(self):
        self.publish("0.3.0")
        fetched = self.skill_fetch()
        self.publish("0.3.1")  # a newer release lands between the consent and the plan
        plan_file, _ = self.skill_plan("upgrade", fetched["provenance"]["version"])
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
        self.assertEqual(plan["to_version"], "0.3.0")

    def test_adoption_of_a_base_without_a_stamp(self):
        repo = self.tmp.path / "template"
        fx.build_history(repo)
        for version in ("0.1.0", "0.2.0"):
            z = fx.zip_of(repo, f"v{version}", self.tmp.path / f"{version}.zip")
            self.archives[f"v{version}.zip"] = z.read_bytes()
        self.latest = "0.2.0"
        self.base = self.tmp.path / "old"
        tree = {p: v for p, v in fx.enc(fx.P0).items() if not p.endswith(".template.md")}
        tree["AGENTS.md"] = b"# Test KB\n\nOwner: Owner\n"
        tree[kt.ONBOARD_VALUES] = json.dumps(fx.VALUES).encode()
        fx.write_tree(self.base, tree)
        fx.git_init(self.base)
        fx.git(self.base, "add", "-A")
        fx.git(self.base, "commit", "-q", "-m", "my base")

        version = self.skill_fetch()["provenance"]["version"]
        plan_file, _ = self.skill_plan("adoption", version)
        self.skill_apply_and_commit(plan_file)
        plan_file, _ = self.skill_plan("upgrade", version)
        self.skill_apply_and_commit(plan_file)
        log = fx.git(self.base, "log", "--format=%s").splitlines()
        self.assertEqual(log[:2], [f"chore(template): upgrade to {fx.REPO} 0.2.0",
                                   f"chore(template): adopt {fx.REPO} 0.1.0"])


class RefusalTest(SkillPathCase):
    """The fix must not open the gate: nothing on disk counts as verified."""

    def setUp(self):
        super().setUp()
        self.publish("0.3.0")
        self.foreign = self.tmp.path / "received" / "release.zip"
        self.foreign.parent.mkdir()
        self.foreign.write_bytes(fx.zip_bytes(fx.template("0.3.0"), comment=COMMIT))

    def assert_refused(self, zip_path: Path) -> str:
        before = fx.tree_hashes(self.base)
        plan_file = self.tmp.path / "plan.json"
        for cmd in (["fetch", "--instance", str(self.base), "--source", str(zip_path)],
                    ["plan", "--instance", str(self.base), "--source", str(zip_path),
                     "--out", str(plan_file)]):
            with self.subTest(command=cmd[0]):
                code, out, err = fx.run(*cmd, opener=self.opener)
                self.assertEqual(code, 1, out)
                self.assertIn("cannot show where it comes from", err)
        self.assertFalse(plan_file.exists())
        self.assertEqual(fx.tree_hashes(self.base), before)
        self.assertEqual(self.downloads, [])
        return err

    def test_foreign_zip_without_consent(self):
        self.assert_refused(self.foreign)

    def test_foreign_zip_with_a_planted_record(self):
        record = {"sha256": kt.content_hash(self.foreign.read_bytes()), "verified": True,
                  "verified_by": f"downloaded over HTTPS from github.com/{fx.REPO}, tag v0.3.0"}
        for name in ("release.zip.json", "release.zip.verified", ".kb-upgrade-verified.json",
                     "verified.json"):
            (self.foreign.parent / name).write_text(json.dumps(record), encoding="utf-8")
        self.assert_refused(self.foreign)

    def test_the_archive_fetch_saved_is_a_plain_zip_afterwards(self):
        archive = Path(self.skill_fetch()["source"]["archive"])
        self.assertTrue(archive.is_file())
        self.downloads.clear()
        err = self.assert_refused(archive)
        # What a base on 0.2.x runs into: its older SKILL.md passes this archive as --source.
        self.assertIn("--to 0.3.0", err)
        self.assertIn(fx.REPO, err)

    def test_no_way_out_is_offered_for_another_repository(self):
        manifest = json.loads(fx.manifest("0.3.0"))
        manifest["repository"] = "someone/fork"
        files = fx.template("0.3.0")
        files[".kb-manifest.json"] = json.dumps(manifest).encode()
        z = self.tmp.path / "fork.zip"
        z.write_bytes(fx.zip_bytes(files))
        code, out, err = fx.run("plan", "--instance", str(self.base), "--source", str(z))
        self.assertEqual(code, 1, out)
        self.assertNotIn("--to", err)

    def test_named_source_with_consent_still_works(self):
        plan_file = self.tmp.path / "plan.json"
        code, out, err = fx.run("plan", "--instance", str(self.base), "--source", str(self.foreign),
                                "--out", str(plan_file), *fx.CONSENT)
        self.assertEqual(code, 0, err)
        self.assertTrue(plan_file.is_file())


if __name__ == "__main__":
    unittest.main()
