"""Unit tests for watch.py. No network: GitHub and URL checks are faked."""
import json
import tempfile
import unittest
from pathlib import Path

import watch

TODAY = "2026-11-13"


class FakeGitHub:
    """Answers watch.GitHub.get() from a dict {path: (status, data)}; unknown -> 404."""
    mode = "fake"

    def __init__(self, routes, remaining=5000):
        self.routes, self.rem, self.calls = routes, remaining, []

    def get(self, path):
        self.calls.append(path)
        return self.routes.get(path, (404, None))

    def remaining(self):
        return self.rem


def repo(full, archived=False, pushed="2026-11-01", lic="MIT"):
    return (200, {"full_name": full, "archived": archived, "disabled": False,
                  "pushed_at": pushed + "T10:00:00Z", "license": {"spdx_id": lic} if lic else None})


def release(tag, date="2026-11-01"):
    return (200, {"tag_name": tag, "published_at": date + "T00:00:00Z"})


def note(fm, body="# Title\n\nSome text.\n"):
    lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    return f"---\n{lines}\n---\n{body}"


class Vault:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def write(self, rel, text, crlf=False):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(text.replace("\n", "\r\n") if crlf else text)
        return p

    def read(self, rel):
        with open(self.root / rel, encoding="utf-8", newline="") as f:
            return f.read()

    def close(self):
        self.tmp.cleanup()


class ProposeTest(unittest.TestCase):
    def test_name_match_wins_over_other_links(self):
        text = "See https://github.com/acme/other and https://github.com/acme/widget-kit."
        self.assertEqual(watch.propose("Widget Kit", "Widget Kit", text),
                         ({"repo": "https://github.com/acme/widget-kit"}, "name-match"))

    def test_single_link(self):
        self.assertEqual(watch.propose("Thing", "Thing", "code: https://github.com/a/b.git")[0],
                         {"repo": "https://github.com/a/b"})

    def test_several_links_are_ambiguous(self):
        prop, basis = watch.propose("Thing", "Thing", "https://github.com/a/b https://github.com/c/d")
        self.assertEqual(prop, {"ambiguous": ["a/b", "c/d"]})
        self.assertIsNone(basis)

    def test_homepage_by_host(self):
        text = "Video https://youtube.com/watch?v=1 and the site https://www.acmetool.io/pricing."
        self.assertEqual(watch.propose("AcmeTool", "AcmeTool", text),
                         ({"homepage": "https://www.acmetool.io/"}, "homepage"))

    def test_homepage_drops_docs_subdomain(self):
        self.assertEqual(watch.propose("Acme", "Acme", "Docs: https://docs.acme.dev/guide")[0],
                         {"homepage": "https://acme.dev/"})
        self.assertEqual(watch.site_root("https://drex.nace.ai/x"), "https://drex.nace.ai/")

    def test_no_links_is_untracked(self):
        self.assertEqual(watch.propose("X", "X", "nothing here")[0], {"untracked": True})

    def test_slug_cannot_leave_the_repos_path(self):
        for bad in ("../user", "a/..", "a/.", ".x/y", "a_b/c", "https://github.com/../../user"):
            self.assertIsNone(watch.gh_slug(bad), bad)
        self.assertEqual(watch.gh_slug("SantanderAI/.github"), "SantanderAI/.github")
        self.assertEqual(watch.gh_slug("https://github.com/my-org/repo.name.git"), "my-org/repo.name")

    def test_github_non_repo_paths_ignored(self):
        self.assertEqual(watch.repo_links("https://github.com/topics/ai https://github.com/orgs/x"), [])


class FlagsTest(unittest.TestCase):
    def n(self, ps="active", checked="2026-08-01"):
        return {"kind": "repo", "repo": "acme/tool", "project_status": ps, "status_checked": checked}

    def f(self, **kw):
        d = {"full_name": "acme/tool", "archived": False, "disabled": False, "pushed_at": "2026-11-01",
             "license": "MIT", "latest": "v1.2.0", "latest_kind": "release"}
        d.update(kw)
        return d

    def base(self, **kw):
        d = self.f(checked="2026-10-13")
        d.update(kw)
        return d

    def kinds(self, n, f, base):
        return [k for k, _ in watch.flags_for(n, f, base, TODAY)]

    def test_nothing_changed(self):
        self.assertEqual(self.kinds(self.n(), self.f(), self.base()), [])

    def test_archived_renamed_licence(self):
        f = self.f(full_name="newco/tool", archived=True, license="GPL-3.0")
        self.assertEqual(self.kinds(self.n(), f, self.base()), ["renamed", "archived", "licence"])

    def test_archived_is_not_news_when_already_dead(self):
        self.assertEqual(self.kinds(self.n(ps="dead"), self.f(archived=True), self.base()), [])

    def test_release_minor_flags_patch_does_not(self):
        self.assertEqual(self.kinds(self.n(), self.f(latest="v1.3.0"), self.base()), ["release"])
        self.assertEqual(self.kinds(self.n(), self.f(latest="v1.2.9"), self.base()), [])

    def test_calendar_version_counts_only_a_new_year(self):
        b = self.base(latest="2026.10.1")
        self.assertEqual(self.kinds(self.n(), self.f(latest="2026.11.0"), b), [])
        self.assertEqual(self.kinds(self.n(), self.f(latest="2027.1.0"), b), ["release"])

    def test_first_release(self):
        b = self.base(latest_kind="none")
        b.pop("latest")
        self.assertEqual(self.kinds(self.n(), self.f(latest="v0.1.0"), b), ["release"])

    def test_no_baseline_no_licence_or_release_flags(self):
        self.assertEqual(self.kinds(self.n(), self.f(), None), [])

    def test_stale_only_on_transition(self):
        old = self.f(pushed_at="2026-03-01")
        self.assertEqual(self.kinds(self.n(), old, self.base(pushed_at="2026-03-01", checked="2026-06-01")), ["stale"])
        self.assertEqual(self.kinds(self.n(), old, self.base(pushed_at="2026-03-01", checked="2026-10-13")), [])
        self.assertEqual(self.kinds(self.n(ps="stale"), old, None), [])

    def test_revived(self):
        n = self.n(ps="stale", checked="2026-09-01")
        self.assertEqual(self.kinds(n, self.f(last_commit="2026-11-02"), self.base()), ["revived"])

    def test_gone(self):
        self.assertEqual(self.kinds(self.n(), {"error": "not-found"}, None), ["gone"])
        self.assertEqual(self.kinds(self.n(ps="dead"), {"error": "not-found"}, None), [])
        self.assertEqual(self.kinds(self.n(), {"error": "network"}, None), [])

    def test_url_dead_but_not_unverified(self):
        n = {"kind": "url", "url": "https://x.io/", "project_status": "active", "status_checked": None}
        self.assertEqual(self.kinds(n, {"status": "dead"}, None), ["unreachable"])
        self.assertEqual(self.kinds(n, {"status": "unverified"}, None), [])
        self.assertEqual(self.kinds(n, {"status": "dead"}, {"status": "dead"}), [])


class SelectTest(unittest.TestCase):
    def test_order_and_budget(self):
        mk = lambda p, kind, sc, flags=(): {"path": p, "kind": kind, "status_checked": sc, "flags": list(flags)}
        notes = [mk("a", "repo", "2026-01-01"), mk("b", "repo", None), mk("c", "url", "2026-02-01"),
                 mk("d", "repo", "2026-11-01"), mk("e", "repo", "2026-11-10", [["archived", "x"]]),
                 mk("f", "untracked", None)]
        watch.select(notes, TODAY, budget=2, due_days=90)
        deep = {n["path"]: n["deep"] for n in notes}
        self.assertTrue(deep["e"].startswith("flagged"))
        self.assertEqual(deep["b"], "never checked")
        self.assertTrue(deep["c"].startswith("due"))
        self.assertIsNone(deep["a"])          # over budget
        self.assertIsNone(deep["d"])          # checked recently
        self.assertIsNone(deep["f"])          # nothing to research it by


class InsertTest(unittest.TestCase):
    BOX = ["> [!success] Status check 2026-11-13 — active", "> **Verdict:** fine."]

    def test_after_h1_and_idempotent(self):
        body = "\n# Tool\n\nIntro text.\n"
        once = watch.insert_callout(body, self.BOX)
        self.assertEqual(once, "\n# Tool\n\n" + "\n".join(self.BOX) + "\n\nIntro text.\n")
        self.assertEqual(watch.insert_callout(once, self.BOX), once)

    def test_replaces_older_box(self):
        old = "# Tool\n\n> [!warning] Status check 2026-01-01 — stale\n> **Verdict:** old.\n\nText\n"
        out = watch.insert_callout(old, self.BOX)
        self.assertNotIn("2026-01-01", out)
        self.assertEqual(out.count("Status check"), 1)

    def test_h1_inside_code_fence_is_skipped(self):
        body = "```\n# not a heading\n```\n# Real\n\nText\n"
        out = watch.insert_callout(body, self.BOX)
        self.assertLess(out.index("# Real"), out.index("Status check"))

    def test_no_h1(self):
        self.assertEqual(watch.insert_callout("\nText\n", self.BOX), "\n" + "\n".join(self.BOX) + "\n\nText\n")


class PrivacyTest(unittest.TestCase):
    def test_terms_and_hits(self):
        v = Vault()
        try:
            v.write("content/_privacy.md", "## Always cut\n\n<!-- - \"Commented\" -->\n- \"Acme Corp\" — client\n\n## Exceptions\n- \"Not me\"\n")
            v.write("content/_privacy.local.md", "## Always cut\n- Zed — client\n")
            terms = watch.private_terms(v.root)
            self.assertEqual(terms, ["Acme Corp", "Zed"])
            self.assertTrue(watch.private_hit("built for acme corp in 2026", terms))
            self.assertFalse(watch.private_hit("Zedboard is a board", terms))   # word boundary
            self.assertTrue(watch.private_hit("https://github.com/acmecorp/tools", terms))
            self.assertTrue(watch.private_hit("acme-corp.com", terms))
        finally:
            v.close()

    def test_private_seed_is_not_written(self):
        v = Vault()
        try:
            v.write("content/_privacy.local.md", "## Always cut\n- \"Acme Corp\"\n")
            v.write("content/CODE/TOOLS/Kit.md", note({"title": '"Kit"', "type": "tool"},
                                                      "# Kit\n\nhttps://github.com/acmecorp/kit\n"))
            scan = watch.run_scan(v.root, TODAY, 0, 90, offline=True)
            before = v.read("content/CODE/TOOLS/Kit.md")
            done = watch.apply_changes(v.root, scan)
            self.assertEqual(done["held"], ["content/CODE/TOOLS/Kit.md"])
            self.assertEqual(v.read("content/CODE/TOOLS/Kit.md"), before)
            self.assertNotIn("acmecorp", watch.build_report(v.root, scan, dry=True))
        finally:
            v.close()


class PipelineTest(unittest.TestCase):
    """scan -> outline -> digest -> apply -> report on a small vault, twice."""

    def setUp(self):
        self.v = Vault()
        v = self.v
        v.write("content/AI/TOOLS/Widget.md", note(
            {"title": '"Widget"', "date": "2026-05-01", "type": "tool", "summary": '"A widget"'},
            "# Widget\n\nRepo: https://github.com/acme/widget\n"), crlf=True)
        v.write("content/AI/TOOLS/Gadget.md", note(
            {"title": '"Gadget"', "date": "2026-05-01", "type": "tool", "repo": '"https://github.com/acme/gadget"',
             "status-checked": "2026-11-01", "project-status": "active"},
            "# Gadget\n\n> [!success] Status check 2026-11-01 — active\n> **Verdict:** fine.\n\nBody.\n"))
        v.write("content/AI/TOOLS/Cloudy.md", note(
            {"title": '"Cloudy"', "date": "2026-05-01", "type": "tool"},
            "# Cloudy\n\nSite: https://cloudy.app/docs\n"))
        v.write("content/AI/TOOLS/Lonely.md", note({"title": '"Lonely"', "type": "tool"}, "# Lonely\n\nNo links.\n"))
        v.write("content/AI/TOOLS/Skipped.md", note({"title": '"Skipped"', "type": "tool", "watch": "false"}, "# S\n"))
        v.write("content/AI/KNOWLEDGE/Map.md", note(
            {"title": '"Map"', "type": "compiled-note", "status-checked": "2026-11-01"}, "# Map\n\n[[Gadget]] [[Widget]]\n"))
        v.write("content/_graveyard/Old.md", note({"title": '"Old"', "type": "tool"}, "# Old\n"))
        self.gh = FakeGitHub({
            "repos/acme/widget": repo("acme/widget"),
            "repos/acme/widget/releases/latest": release("v2.0.0"),
            "repos/acme/gadget": repo("acme-labs/gadget", archived=True),
            "repos/acme-labs/gadget/releases/latest": release("v1.0.0"),
        })

    def tearDown(self):
        self.v.close()

    def scan(self, gh=None, budget=40):
        return watch.run_scan(self.v.root, TODAY, budget, 90, gh=gh or self.gh,
                              url_check=lambda u: "alive", workers=2)

    def test_end_to_end(self):
        root, ws = self.v.root, self.v.root / "ws"
        scan = self.scan()
        by = {n["stem"]: n for n in scan["notes"]}
        self.assertEqual(sorted(by), ["Cloudy", "Gadget", "Lonely", "Widget"])
        self.assertEqual(by["Widget"]["seed"], {"repo": "https://github.com/acme/widget"})
        self.assertEqual(by["Cloudy"]["seed"], {"homepage": "https://cloudy.app/"})
        self.assertEqual(by["Lonely"]["kind"], "untracked")
        self.assertEqual([k for k, _ in by["Gadget"]["flags"]], ["renamed", "archived"])
        self.assertEqual(by["Widget"]["deep"], "never checked")
        self.assertEqual(scan["aggregators"][0]["links"], ["Gadget", "Widget"])
        for call in self.gh.calls:
            self.assertTrue(call == "rate_limit" or call.startswith("repos/acme"), call)

        self.assertEqual(watch.build_outline(scan, ws), 3)
        result = {"repo_url": "https://github.com/acme-labs/gadget", "moved_or_renamed": "acme -> acme-labs",
                  "last_release": "v1.0.0 (2026-11-01)", "last_commit": "2026-11-01", "archived_or_deprecated":
                  "Archived on 2026-11-10.", "license": "MIT", "liveness": "dead",
                  "liveness_evidence": "The repository was archived on 2026-11-10 after the v1.0.0 release.",
                  "successor_or_replacement": "Use Widget, which does the same job.",
                  "changes_since_note": "The project was archived and moved to acme-labs. The note still calls it active.",
                  "sources": ["https://github.com/acme-labs/gadget"], "uncertain": []}
        (ws / "results" / "Gadget.json").write_text(json.dumps(result), encoding="utf-8")
        w = dict(result, repo_url="https://github.com/acme/widget", moved_or_renamed="no", archived_or_deprecated="no",
                 liveness="active", liveness_evidence="Released v2.0.0 on 2026-11-01, commits weekly.",
                 successor_or_replacement="n/a", changes_since_note="nothing material")
        (ws / "results" / "Widget.json").write_text(json.dumps(w), encoding="utf-8")
        dg = watch.build_digest(root, scan, ws)
        self.assertEqual(sorted(dg["notes"]), ["content/AI/TOOLS/Gadget.md", "content/AI/TOOLS/Widget.md"])
        self.assertEqual(dg["missing"], ["content/AI/TOOLS/Cloudy.md"])
        g = dg["notes"]["content/AI/TOOLS/Gadget.md"]
        self.assertEqual(g["repo"], "https://github.com/acme-labs/gadget")
        self.assertTrue(g["enhance"])
        self.assertIn("[[Widget]]", " ".join(g["lines"]))
        self.assertFalse(dg["notes"]["content/AI/TOOLS/Widget.md"]["enhance"])

        before = {p: self.v.read(p) for p in ("content/AI/TOOLS/Widget.md", "content/AI/TOOLS/Gadget.md")}
        dry = watch.apply_changes(root, scan, dg, dry=True)
        self.assertEqual(sorted(dry["status"]), sorted(dg["notes"]))
        self.assertEqual({p: self.v.read(p) for p in before}, before)
        self.assertFalse((root / watch.SNAPSHOT).exists())

        watch.apply_changes(root, scan, dg)
        wid = self.v.read("content/AI/TOOLS/Widget.md")
        self.assertIn("\r\n", wid)
        self.assertNotIn("\n\n\n", wid.replace("\r\n", "\n"))
        self.assertIn('repo: "https://github.com/acme/widget"', wid)
        self.assertIn("status-checked: 2026-11-13", wid)
        self.assertIn("> [!success] Status check 2026-11-13 — active", wid)
        gad = self.v.read("content/AI/TOOLS/Gadget.md")
        self.assertIn('repo: "https://github.com/acme-labs/gadget"', gad)
        self.assertIn("project-status: dead", gad)
        self.assertEqual(gad.count("Status check"), 1)
        self.assertIn("Body.", gad)
        snap = json.loads((root / watch.SNAPSHOT).read_text(encoding="utf-8"))
        self.assertEqual(sorted(snap["repos"]), ["acme-labs/gadget", "acme/widget"])
        self.assertEqual(snap["urls"]["https://cloudy.app/"]["status"], "alive")

        report = watch.build_report(root, scan, dg)
        self.assertIn("`/b:enhance [[Gadget]]`", report)
        self.assertIn("[[Gadget]] — dead", report)
        self.assertIn("[[Map]] links [[Gadget]]", report)
        self.assertIn("[[Lonely]] — no repo or product link", report)

        # Second run: same world, nothing to write, nothing due.
        gh2 = FakeGitHub(dict(self.gh.routes, **{
            "repos/acme-labs/gadget": repo("acme-labs/gadget", archived=True)}))
        again = self.scan(gh=gh2)
        by2 = {n["stem"]: n for n in again["notes"]}
        self.assertEqual([n["stem"] for n in again["notes"] if n["flags"]], [])
        self.assertEqual(by2["Cloudy"]["deep"], "never checked")
        self.assertEqual(by2["Widget"]["seed"], {})
        files = {p.as_posix(): p.read_bytes() for p in (root / "content").rglob("*.md")}
        done = watch.apply_changes(root, again, {"notes": {}})
        self.assertEqual(done["seeded"] + done["status"], [])
        self.assertEqual({p.as_posix(): p.read_bytes() for p in (root / "content").rglob("*.md")}, files)

    def test_unresearched_flag_survives_to_next_run(self):
        watch.write_json(self.v.root / watch.SNAPSHOT, {"repos": {"acme/gadget": {
            "full_name": "acme/gadget", "archived": False, "license": "MIT", "latest": "v1.0.0",
            "latest_kind": "release", "pushed_at": "2026-11-01", "checked": "2026-10-13"}}, "urls": {}})
        scan = self.scan()
        self.assertIn("archived", [k for n in scan["notes"] for k, _ in n["flags"]])
        watch.apply_changes(self.v.root, scan, {"notes": {}})       # deep pass did not run
        snap = watch.load_snapshot(self.v.root)
        self.assertFalse(snap["repos"]["acme/gadget"]["archived"])
        again = self.scan()
        self.assertIn("archived", [k for n in again["notes"] for k, _ in n["flags"]])

    def test_licence_added_later_is_flagged(self):
        routes = dict(self.gh.routes, **{"repos/acme/widget": repo("acme/widget", lic=None)})
        watch.apply_changes(self.v.root, self.scan(gh=FakeGitHub(routes)))
        self.assertIsNone(watch.load_snapshot(self.v.root)["repos"]["acme/widget"]["license"])
        flags = {n["stem"]: [k for k, _ in n["flags"]] for n in self.scan()["notes"]}
        self.assertEqual(flags["Widget"], ["licence"])

    def test_rename_into_a_private_org_is_held(self):
        self.v.write("content/_privacy.local.md", "## Always cut\n- \"Acme Labs\"\n")
        scan = self.scan()                      # Gadget: acme/gadget -> acme-labs/gadget
        ws = self.v.root / "ws"
        watch.build_outline(scan, ws, self.v.root)
        r = {"repo_url": "moved", "moved_or_renamed": "moved", "last_release": "v1.0.0",
             "last_commit": "2026-11-01", "archived_or_deprecated": "archived", "license": "MIT",
             "liveness": "dead", "liveness_evidence": "Archived.", "successor_or_replacement": "n/a",
             "changes_since_note": "Archived.", "sources": []}
        (ws / "results" / "Gadget.json").write_text(json.dumps(r), encoding="utf-8")
        dg = watch.build_digest(self.v.root, scan, ws)
        self.assertNotIn("content/AI/TOOLS/Gadget.md", dg["notes"])
        self.assertEqual([h["path"] for h in dg["held"]], ["content/AI/TOOLS/Gadget.md"])

    def test_rate_limit_skips_rest(self):
        scan = self.scan(gh=FakeGitHub(self.gh.routes, remaining=28))
        errs = sorted((n["facts"].get("error") or "ok") for n in scan["notes"] if n["kind"] == "repo")
        self.assertEqual(errs, ["ok", "skipped-rate-limit"])

    def test_private_term_holds_the_box(self):
        self.v.write("content/_privacy.local.md", "## Always cut\n- \"Secret Client\"\n")
        scan = self.scan()
        ws = self.v.root / "ws"
        watch.build_outline(scan, ws)
        r = {"repo_url": "https://github.com/acme/widget", "moved_or_renamed": "no", "last_release": "v2.0.0",
             "last_commit": "2026-11-01", "archived_or_deprecated": "no", "license": "MIT", "liveness": "active",
             "liveness_evidence": "Used by Secret Client since 2026.", "successor_or_replacement": "n/a",
             "changes_since_note": "nothing material", "sources": []}
        (ws / "results" / "Widget.json").write_text(json.dumps(r), encoding="utf-8")
        self.v.write("content/_privacy.local.md", "## Always cut\n- \"Secret Client\"\n- \"Acme\"\n")
        watch.build_outline(scan, ws, self.v.root)
        self.assertNotIn("acme", (ws / "outline.yaml").read_text(encoding="utf-8").lower())
        self.v.write("content/_privacy.local.md", "## Always cut\n- \"Secret Client\"\n")
        dg = watch.build_digest(self.v.root, scan, ws)
        self.assertNotIn("content/AI/TOOLS/Widget.md", dg["notes"])
        self.assertEqual(dg["held"][0]["reason"], "a line matched a private term")
        self.assertNotIn("Secret Client", watch.build_report(self.v.root, scan, dg))


if __name__ == "__main__":
    unittest.main()
