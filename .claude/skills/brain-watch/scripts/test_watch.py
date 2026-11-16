"""Unit tests for watch.py. No network: GitHub and URL checks are faked."""
import hashlib
import html
import json
import re
import tempfile
import unittest
from pathlib import Path

import watch

TODAY = "2026-11-13"
HOSTILE = ("<script>alert(1)</script> <img src=x onerror=alert(1)> &lt;svg onload=alert(1)&gt; "
           "![p](https://evil.example/p.png) ![[Secret.png]] [x](javascript:alert(1)) "
           "==<b onmouseover=alert(1)>hi</b>== [\\[Note|<i>alias</i>]] %% hidden %% $1 and $2 #injected")


# Quartz's wikilinkRegex (quartz/plugins/transformers/ofm.ts).
OFM_WIKILINK = re.compile(r"!?\[\[([^\[\]|#\\]+)?(#+[^\[\]|#\\]+)?(\\?\|[^\[\]#]+)?\]\]")


def decoded(md):
    """Roughly the text Quartz's Obsidian plugin scans after Markdown parsing: backslash
    escapes and character references resolved."""
    return html.unescape(re.sub(r"\\([!-/:-@\[-`{-~])", r"\1", md))


def assert_inert(case, md, notes=("Widget", "Gadget")):
    """md shows its text as text on a Quartz site: no raw HTML, image, embed, highlight,
    comment or non-http(s) link; wikilinks only to `notes`."""
    case.assertNotRegex(md, r"<[A-Za-z/!]")
    case.assertNotIn("![", md)
    case.assertNotIn("%%", md)
    case.assertNotRegex(md, r"\]\((?!https?://)")
    case.assertNotIn("==", decoded(md))
    for text in (md, decoded(md)):          # Quartz reads wikilinks in both
        for m in OFM_WIKILINK.finditer(text):
            case.assertEqual(m.group(0), f"[[{m.group(1)}]]")          # no embed, alias or anchor
            case.assertIn(m.group(1), notes)
    case.assertNotIn("![[", decoded(md))                                # an embed
    case.assertNotRegex(md, r"\]\][(\[]")                              # [[x]] as a link label
    case.assertNotRegex(decoded(md), r"(?m)(?:^| )#[^\s#]")         # a Quartz #tag


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


class FrontmatterTest(unittest.TestCase):
    def test_append_and_replace(self):
        out = watch.set_fm('title: "X"\ntype: tool', "repo", '"u"')
        self.assertEqual(out, 'title: "X"\ntype: tool\nrepo: "u"')
        self.assertEqual(watch.set_fm(out, "repo", '"v"'), 'title: "X"\ntype: tool\nrepo: "v"')

    def test_append_keeps_blank_line_before_closing_fence(self):
        text = '---\ntitle: "X"\ntype: tool\n\n---\n# X\n'
        fm, body = watch.split_fm(text)
        out = watch.set_fm(fm, "homepage", '"https://x.example/"')
        self.assertEqual(out, 'title: "X"\ntype: tool\nhomepage: "https://x.example/"\n')


class SafeMarkdownTest(unittest.TestCase):
    def test_hostile_text_is_inert(self):
        out = watch.safe_md(HOSTILE)
        assert_inert(self, out)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", out)
        self.assertIn("[p](https://evil.example/p.png)", out)     # an image becomes a link
        self.assertIn("\\$1 and \\$2", out)

    def test_twice_is_once(self):
        for s in (HOSTILE, "a & b &amp; c &#60; &nbsp; <x>", "[[Widget]] and [[Other]]",
                  "https://ok.example/a?b=1&c=2 and https://bad.example/a(b)", "\\$5, \\\\$6",
                  "https://ok.example/<img src=x> and https://bad.example/a&quot;b", "#tag, #1, C# and # x"):
            once = watch.safe_md(s, {"Widget"})
            self.assertEqual(watch.safe_md(once, {"Widget"}), once, s)

    def test_character_references_are_escaped(self):
        self.assertEqual(watch.safe_md("&#60;b&#62; &nbsp; a & b"), "&amp;#60;b&amp;#62; &amp;nbsp; a & b")

    def test_links_only_to_checked_http_urls(self):
        self.assertEqual(watch.safe_md("[docs](https://ok.example/a?b=1&c=2#x)"),
                         "[docs](https://ok.example/a?b=1&c=2#x)")
        for bad in ("javascript:alert(1)", "javascript:void", "data:text/html,x", "https://ok.example/\"x",
                    "//evil.example/", "https://user@evil.example/", "https://ok.example/&lt;x"):
            out = watch.safe_md(f"[docs]({bad})")
            self.assertNotRegex(out, r"\]\((?!https?://)", bad)
            self.assertIn("docs", out)
        self.assertNotIn("](javascript", watch.safe_md("[a [b] c](javascript:alert(1))"))
        self.assertEqual(watch.safe_md("see https://ok.example/x."), "see https://ok.example/x.")
        self.assertEqual(watch.safe_md("(https://ok.example/x)"), "(https://ok.example/x)")
        self.assertEqual(watch.safe_md("https://bad.example/a(b)"), "https://bad.example/a(b)")  # text
        self.assertNotRegex(watch.safe_md("[x](https://bad.example/a(b))"), r"\]\(")
        self.assertTrue(watch.safe_md("[ref]: javascript:alert(1)").startswith("\\[ref]:"))
        self.assertIsNone(watch.safe_url("javascript:alert(1)"))
        self.assertEqual(watch.safe_url("https://github.com/a/b"), "https://github.com/a/b")

    def test_tags_are_not_made(self):
        self.assertEqual(watch.safe_md("#tag first, then #other, but C# and # x"),
                         watch.NBSP + "#tag first, then" + watch.NBSP + "#other, but C# and # x")

    def test_wikilinks_only_to_known_notes(self):
        out = watch.safe_md("Use [[Widget]], not [[Other]], [[Widget|<b>x</b>]] or ![[Widget]]", {"Widget"})
        self.assertEqual(out.count("[[Widget]]"), 1)
        assert_inert(self, out)

    def test_nothing_pairs_with_what_is_put_back(self):
        # Kept URLs and [[links]] go back in after the rules ran: the text that lands next
        # to them must not make a highlight, image, embed or link out of them.
        for s in ("xhttps://a.example/==<script>alert(1)</script>xhttps://b.example/==",
                  "[](https://a.example/?q=)=<b>x</b>[](https://b.example/?q=)=",
                  "see https://a.example/==x== ok",
                  "!![p](https://evil.example/p.png)", "[!](bad)[p](https://evil.example/p.png)",
                  "!![](javascript:x)[[Widget]]", "[!](bad)[[Widget]]", "!\\[](bad)[[Widget]]",
                  "[[Widget]](javascript:alert(1))", "[[Widget]][x](https://ok.example/)",
                  "[[Widget]][[Widget]] and [[[Widget]]](javascript:alert(1))"):
            out = watch.safe_md(s, {"Widget"})
            assert_inert(self, out)
            self.assertEqual(watch.safe_md(out, {"Widget"}), out, s)
        self.assertEqual(watch.safe_md("[t](https://ok.example/?k=YQ==) and [[Widget]]", {"Widget"}),
                         "[t](https://ok.example/?k=YQ==) and [[Widget]]")    # == in a link target is fine


class PrivacyTest(unittest.TestCase):
    def test_folded_forms_match_names_without_polish_letters(self):
        terms = ["Żywłok Mąćski"]                               # a made-up name
        for text in ("clients/zywlok-macski/plan.md", "Zywlok Macski", "ZYWLOKMACSKI",
                     "żywłok_mąćski", "met ŻYWŁOK MĄĆSKI"):
            self.assertTrue(watch.private_hit(text, terms), text)
        self.assertFalse(watch.private_hit("zywlokmacskiego", terms))   # still a whole word
        self.assertEqual(watch.redact("see zywlok-macski here", terms), "see [private] here")
        self.assertIn("Zywlok-Macski", watch.term_forms("Żywłok Mąćski"))

    def test_short_folded_form_is_left_out(self):
        self.assertEqual(watch.term_forms("Wąs"), {"Wąs"})       # folded, it would be "was"
        self.assertTrue(watch.private_hit("Wąs", ["Wąs"]))
        self.assertFalse(watch.private_hit("it was fine", ["Wąs"]))
        self.assertTrue(watch.private_hit("gzel.example", ["Gżel"]))  # four letters: folded too

    def test_snapshot_key(self):
        terms = ["Vexmoor"]                                      # a made-up name
        self.assertEqual(watch.snapshot_key("acme/widget", terms), "acme/widget")
        hidden = watch.snapshot_key("vexmoor/kit", terms)
        self.assertTrue(hidden.startswith("private:"))
        self.assertNotIn(hashlib.sha256(b"vexmoor/kit").hexdigest()[:32], hidden)  # keyed, not a plain hash
        self.assertEqual(watch.snapshot_key("vexmoor/kit", terms), hidden)
        self.assertNotEqual(watch.snapshot_key("vexmoor/kit", terms + ["Other"]), hidden)

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

    def test_report_shows_the_repo_apply_wrote(self):
        root, ws = self.v.root, self.v.root / "ws"
        self.v.write("content/AI/TOOLS/Shifter.md", note(  # title != repo name: a single-link seed
            {"title": '"Shifter"', "type": "tool"}, "# Shifter\n\nCode: https://github.com/acme/mover\n"))
        self.v.write("content/AI/TOOLS/Suite.md", note(
            {"title": '"Suite"', "type": "tool"}, "# Suite\n\nSite: https://www.bigvendor.example/suite\n"))
        gh = FakeGitHub(dict(self.gh.routes, **{
            "repos/acme/mover": repo("acme-labs/mover"),
            "repos/acme-labs/mover/releases/latest": release("v1.0.0")}))
        scan = self.scan(gh=gh)
        watch.build_outline(scan, ws)
        r = {"repo_url": "https://github.com/acme-labs/mover", "moved_or_renamed": "acme -> acme-labs",
             "last_release": "v1.0.0", "last_commit": "2026-11-01", "archived_or_deprecated": "no",
             "license": "MIT", "liveness": "active", "liveness_evidence": "Released v1.0.0.",
             "successor_or_replacement": "n/a", "changes_since_note": "nothing material",
             "sources": ["https://github.com/acme-labs/mover"], "uncertain": []}
        (ws / "results" / "Shifter.json").write_text(json.dumps(r), encoding="utf-8")
        dg = watch.build_digest(root, scan, ws)
        watch.apply_changes(root, scan, dg)
        self.assertIn('repo: "https://github.com/acme-labs/mover"', self.v.read("content/AI/TOOLS/Shifter.md"))
        report = watch.build_report(root, scan, dg)
        self.assertIn("[[Shifter]] → https://github.com/acme-labs/mover (moved from https://github.com/acme/mover)",
                      report)
        self.assertNotIn("check these", report)  # the deep pass already checked Shifter's link
        self.assertIn("[[Suite]] — one link, but its site is not named after the note: "
                      "https://www.bigvendor.example/suite", report)

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

    def test_hostile_results_and_overrides_are_written_as_text(self):
        root, ws = self.v.root, self.v.root / "ws"
        scan = self.scan()
        watch.build_outline(scan, ws)
        r = {"repo_url": "https://evil.example/<img src=x onerror=alert(1)>", "moved_or_renamed": HOSTILE,
             "last_release": HOSTILE, "last_commit": HOSTILE, "archived_or_deprecated": HOSTILE,
             "license": HOSTILE, "liveness": "dead", "liveness_evidence": HOSTILE,
             "successor_or_replacement": "Use Widget. " + HOSTILE, "changes_since_note": HOSTILE, "sources": []}
        (ws / "results" / "Gadget.json").write_text(json.dumps(r), encoding="utf-8")
        (ws / "overrides.json").write_text(json.dumps({"Widget": {"liveness": "active", "lines": [
            "**Verdict:** " + HOSTILE, "[ref]: javascript:alert(1)", "two\nlines <iframe src=x>"]}}),
            encoding="utf-8")
        dg = watch.build_digest(root, scan, ws)
        for e in dg["notes"].values():
            for line in e["lines"] + [e["changes"]]:
                assert_inert(self, line)
        # digest.json may be edited (translated) before apply: apply escapes again.
        dg["notes"]["content/AI/TOOLS/Widget.md"]["lines"].append("<script>alert(2)</script>")
        watch.apply_changes(root, scan, dg)
        for stem in ("Gadget", "Widget"):
            box = [x[2:] for x in self.v.read(f"content/AI/TOOLS/{stem}.md").replace("\r\n", "\n").split("\n")
                   if x.startswith("> ") and "Status check" not in x]
            self.assertTrue(box, stem)
            for line in box:
                assert_inert(self, line)
                self.assertNotIn("javascript:", line.split("](")[-1][:11])
        gad = self.v.read("content/AI/TOOLS/Gadget.md")
        self.assertIn("> **Source:** https://evil.example/&lt;img src=x", gad)   # failed the URL check
        self.assertIn("[[Widget]]", gad)                                    # the skill's own wikilink
        wid = self.v.read("content/AI/TOOLS/Widget.md")
        self.assertIn("> \\[ref]: javascript", wid)                        # no link definition
        self.assertIn("> two lines &lt;iframe src=x&gt;", wid.replace("\r\n", "\n"))
        report = watch.build_report(root, scan, dg)
        assert_inert(self, report.split("<details><summary>All seeded notes</summary>")[0],
                     ("Widget", "Gadget", "Map", "Lonely"))

    def test_report_keeps_its_details_wrapper_and_escapes_github_text(self):
        watch.write_json(self.v.root / watch.SNAPSHOT, {"repos": {"acme/widget": {
            "full_name": "acme/widget", "archived": False, "license": "MIT", "latest_kind": "none",
            "pushed_at": "2026-11-01", "checked": "2026-10-13"}}, "urls": {}})
        gh = FakeGitHub(dict(self.gh.routes, **{
            "repos/acme/widget": (200, {"full_name": "acme/widget", "pushed_at": "2026-11-01T00:00:00Z",
                                        "license": {"spdx_id": "<img src=x onerror=alert(1)>"}}),
            "repos/acme/widget/releases/latest": release("v1.0<svg/onload=alert(1)>")}))
        scan = self.scan(gh=gh)
        report = watch.build_report(self.v.root, scan, dry=True)
        self.assertIn("\n<details><summary>All seeded notes</summary>\n", report)
        self.assertIn("\n</details>\n", report)
        flags = [x for x in report.split("\n")
                 if x.startswith(("| [[Widget]] | licence |", "| [[Widget]] | release |"))]
        self.assertEqual(len(flags), 2, report)
        for line in flags:
            assert_inert(self, line)
        self.assertIn("&lt;svg/onload=alert(1)&gt;", report)

    def test_snapshot_keeps_private_names_out(self):
        self.v.write("content/_privacy.local.md", "## Always cut\n- \"Vexmoor\"\n")   # a made-up name
        self.v.write("content/AI/TOOLS/Kit.md", note(
            {"title": '"Kit"', "type": "tool", "repo": '"https://github.com/vexmoor/kit"'}, "# Kit\n"))
        self.v.write("content/AI/TOOLS/Portal.md", note(
            {"title": '"Portal"', "type": "tool", "homepage": '"https://vexmoor-portal.example/"'}, "# Portal\n"))
        self.v.write("content/AI/TOOLS/Spare.md", note(     # public repo, private release tag
            {"title": '"Spare"', "type": "tool", "repo": '"https://github.com/acme/spare"'}, "# Spare\n"))
        routes = dict(self.gh.routes, **{
            "repos/vexmoor/kit": repo("vexmoor/kit"), "repos/vexmoor/kit/releases/latest": release("v1.0.0"),
            "repos/acme/spare": repo("acme/spare"), "repos/acme/spare/releases/latest": release("vexmoor-2.0")})
        watch.apply_changes(self.v.root, self.scan(gh=FakeGitHub(routes)))
        raw = (self.v.root / watch.SNAPSHOT).read_text(encoding="utf-8")
        self.assertNotIn("vexmoor", raw.lower())
        snap = json.loads(raw)
        hidden = [k for k in list(snap["repos"]) + list(snap["urls"]) if k.startswith("private:")]
        self.assertEqual(len(hidden), 2)                       # Kit's repo, Portal's URL
        self.assertEqual(snap["repos"]["acme/spare"]["license"], "MIT")
        self.assertNotIn("latest_kind", snap["repos"]["acme/spare"])
        self.assertIn("acme/widget", snap["repos"])

        flags = lambda scan: {n["stem"]: [k for k, _ in n["flags"]] for n in scan["notes"]}
        again = flags(self.scan(gh=FakeGitHub(routes)))      # the hashed baseline is found
        self.assertEqual((again["Kit"], again["Spare"], again["Portal"]), ([], [], []))
        routes["repos/vexmoor/kit"] = repo("vexmoor/kit", lic="GPL-3.0")
        self.assertEqual(flags(self.scan(gh=FakeGitHub(routes)))["Kit"], ["licence"])

    def test_private_entry_from_an_older_snapshot_is_read_then_hashed(self):
        self.v.write("content/_privacy.local.md", "## Always cut\n- \"Vexmoor\"\n")
        self.v.write("content/AI/TOOLS/Kit.md", note(
            {"title": '"Kit"', "type": "tool", "repo": '"https://github.com/vexmoor/kit"'}, "# Kit\n"))
        watch.write_json(self.v.root / watch.SNAPSHOT, {"repos": {"vexmoor/kit": {
            "full_name": "vexmoor/kit", "archived": False, "license": "MIT", "latest": "v1.0.0",
            "latest_kind": "release", "pushed_at": "2026-11-01", "checked": "2026-10-13"}}, "urls": {}})
        routes = dict(self.gh.routes, **{"repos/vexmoor/kit": repo("vexmoor/kit", archived=True),
                                         "repos/vexmoor/kit/releases/latest": release("v1.0.0")})
        scan = self.scan(gh=FakeGitHub(routes))
        self.assertEqual({n["stem"]: [k for k, _ in n["flags"]] for n in scan["notes"]}["Kit"], ["archived"])
        watch.apply_changes(self.v.root, scan, {"notes": {}})   # flagged, not researched: keep the old entry
        raw = (self.v.root / watch.SNAPSHOT).read_text(encoding="utf-8")
        self.assertNotIn("vexmoor", raw.lower())
        old = [v for k, v in json.loads(raw)["repos"].items() if k.startswith("private:")]
        self.assertEqual(len(old), 1)
        self.assertFalse(old[0]["archived"])                     # the flag survives to the next run

    def test_private_term_changed_by_escaping_is_still_held(self):
        self.v.write("content/_privacy.local.md", "## Always cut\n- \"Vexmoor #2\"\n")   # made up
        scan = self.scan()
        ws = self.v.root / "ws"
        watch.build_outline(scan, ws, self.v.root)
        r = {"repo_url": "https://github.com/acme/widget", "moved_or_renamed": "no", "last_release": "v2.0.0",
             "last_commit": "2026-11-01", "archived_or_deprecated": "no", "license": "MIT", "liveness": "active",
             "liveness_evidence": "Used by Vexmoor #2 since 2026.", "successor_or_replacement": "n/a",
             "changes_since_note": "nothing material", "sources": []}
        (ws / "results" / "Widget.json").write_text(json.dumps(r), encoding="utf-8")
        self.assertNotIn("Vexmoor #2", watch.safe_md(r["liveness_evidence"]))   # the space became NBSP
        dg = watch.build_digest(self.v.root, scan, ws)
        self.assertNotIn("content/AI/TOOLS/Widget.md", dg["notes"])

    def test_apply_checks_an_edited_digest_again(self):
        self.v.write("content/_privacy.local.md", "## Always cut\n- \"Vexmoor\"\n")   # a made-up name
        scan, path = self.scan(), "content/AI/TOOLS/Widget.md"
        for entry in ({"liveness": "active", "lines": ["Now run by Vexmoor."]},   # added by a translation
                      {"liveness": "active\ntitle: x", "lines": ["fine"]}):
            done = watch.apply_changes(self.v.root, scan, {"notes": {path: entry}}, dry=True)
            self.assertIn(path, done["held"], entry)
            self.assertNotIn(path, done["status"], entry)

    def test_report_checks_private_terms_before_escaping(self):
        self.v.write("content/_privacy.local.md", "## Always cut\n- \"Vexmoor #2\"\n")   # made up
        watch.write_json(self.v.root / watch.SNAPSHOT, {"repos": {"acme/widget": {
            "full_name": "acme/widget", "archived": False, "license": "MIT", "latest_kind": "none",
            "pushed_at": "2026-11-01", "checked": "2026-10-13"}}, "urls": {}})
        gh = FakeGitHub(dict(self.gh.routes, **{
            "repos/acme/widget/releases/latest": release("Vexmoor #2 build")}))
        report = watch.build_report(self.v.root, self.scan(gh=gh), dry=True)
        self.assertNotIn("vexmoor", report.lower())
        self.assertIn("(withheld: a private term)", report)

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
