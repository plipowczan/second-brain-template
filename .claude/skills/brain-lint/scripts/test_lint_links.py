import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LINT_LINKS = Path(__file__).resolve().parent / "lint_links.py"

# A vault that exercises every rule of lint_links.py: aliases, headings, a pipe escaped
# inside a table, a link that differs only in case, links inside code, attachments,
# templates, a self-link, duplicate file names in two folders, non-ASCII names, and the
# folders and files the script skips. Invented names only.
FIXTURE = {
    "T/Hub.md": "# Hub\n[[Target]] [[T/Target]] [[Target|alias]] [[Target#Part]] [[Target]]\n"
                "| a | [[Leaf\\|shown]] |\n[[lonely-lower]] [[Missing Note]] [[pic.png]]\n"
                "[[templates/Note Template]] [[ATTACHMENTS/scan.pdf]] [[Zażółć]]\n",
    "T/Target.md": "# Target\nBack to [[Hub]].\n```\n[[Only In Code]]\n```\nand `[[Inline Code]]`\n",
    "T/Leaf.md": "# Leaf\nNo links here.\n",
    "T/Self.md": "# Self\nSee [[Self]].\n",
    "T/Lonely-Lower.md": "# Lonely lower\n",
    "T/Zażółć.md": "# Zażółć\n[[gęś]]\n",
    "A/Dup.md": "# Dup A\n[[Dup]]\n",
    "B/Dup.md": "# Dup B\n[[B/Dup]] [[Nowhere/Else]]\n",
    "Root Note.md": "# Root\n[[Leaf]] [[]] [[ ]]\n",
    "_privacy.md": "# Privacy\n[[Hub]]\n",
    "WRITING_STYLE.md": "# Style\n[[Leaf]]\n",
    "T/Draft.template.md": "# Template\n[[Leaf]]\n",
    "_outputs/answers/a.md": "# Answer\n[[Lonely-Lower]]\n",
    "_raw/inbox/x.md": "[[Self]]\n",
    "ATTACHMENTS/inside.md": "[[Leaf]]\n",
    "templates/Note Template.md": "# T\n[[Leaf]]\n",
    ".obsidian/x.md": "[[Leaf]]\n",
}

# Recorded from lint_links.py as it was before it became importable (2026-11-27, the
# commit that adds this test). A rewrite must print the same.
GOLDEN = {
    "broken": {
        "content/B/Dup.md": ["Nowhere/Else"],
        "content/T/Hub.md": ["Missing Note"],
        "content/T/Zażółć.md": ["gęś"],
    },
    "orphan_count": 1,
    "orphans": ["Root Note"],
}


def build_fixture(root):
    """Write FIXTURE under <root>/content and return that folder."""
    content = Path(root) / "content"
    for rel, text in FIXTURE.items():
        path = content / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return content


def run_in(vault):
    r = subprocess.run([sys.executable, str(LINT_LINKS)], cwd=vault,
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class TestUnderscoreFiles(unittest.TestCase):
    def test_underscore_prefixed_file_is_not_an_orphan(self):
        with tempfile.TemporaryDirectory() as d:
            content = Path(d) / "content"
            (content / "T").mkdir(parents=True)
            (content / "_privacy.md").write_text("# Privacy rules\n", encoding="utf-8")
            (content / "T" / "_draft.md").write_text("# Draft\n", encoding="utf-8")
            (content / "T" / "Lonely.md").write_text("# Lonely\n", encoding="utf-8")
            self.assertEqual(run_in(d)["orphans"], ["Lonely"])


class TestGoldenOutput(unittest.TestCase):
    """Pins what the script prints, so a rewrite cannot change it unnoticed. Compared as
    parsed JSON: the order of `broken` follows os.walk, which differs between systems."""

    def test_fixture_output_is_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            build_fixture(d)
            self.assertEqual(run_in(d), GOLDEN)

    def test_empty_vault(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "content").mkdir()
            self.assertEqual(run_in(d), {"broken": {}, "orphan_count": 0, "orphans": []})


class TestScanFunction(unittest.TestCase):
    """scan() is what metrics.py builds on: the same notes, incoming names, broken links
    and orphans the script prints, plus the edges between notes."""

    def scan(self):
        sys.path.insert(0, str(LINT_LINKS.parent))
        import lint_links
        with tempfile.TemporaryDirectory() as d:
            content = build_fixture(d)
            result = lint_links.scan(str(content))
            prefix = str(content).replace("\\", "/") + "/"
        strip = (lambda p: p[len(prefix):])
        return lint_links, result, strip

    def test_matches_the_printed_report(self):
        lint_links, result, strip = self.scan()
        report = lint_links.report(result)
        self.assertEqual({"content/" + strip(p): v for p, v in report["broken"].items()},
                         GOLDEN["broken"])
        self.assertEqual(report["orphans"], GOLDEN["orphans"])
        self.assertEqual(report["orphan_count"], GOLDEN["orphan_count"])
        self.assertEqual([strip(p) for p, _ in result["orphan_notes"]], ["Root Note.md"])

    def test_notes(self):
        _, result, strip = self.scan()
        self.assertEqual(sorted(strip(p) for p, _ in result["notes"]), [
            "A/Dup.md", "B/Dup.md", "Root Note.md", "T/Hub.md", "T/Leaf.md",
            "T/Lonely-Lower.md", "T/Self.md", "T/Target.md", "T/Zażółć.md"])
        self.assertTrue(all(strip(p).endswith(n + ".md") for p, n in result["notes"]))

    def test_edges_and_other_links(self):
        _, result, strip = self.scan()
        edges = sorted((strip(p), t) for p, t in result["edges"])
        self.assertEqual(edges, sorted([
            ("A/Dup.md", "Dup"), ("B/Dup.md", "Dup"), ("Root Note.md", "Leaf"),
            ("T/Hub.md", "Leaf"), ("T/Hub.md", "Zażółć"), ("T/Hub.md", "lonely-lower"),
            ("T/Hub.md", "Target"), ("T/Hub.md", "Target"), ("T/Hub.md", "Target"),
            ("T/Hub.md", "Target"), ("T/Hub.md", "Target"), ("T/Self.md", "Self"),
            ("T/Target.md", "Hub")]))
        self.assertEqual(sorted((strip(p), t) for p, t in result["other_links"]), [
            ("T/Hub.md", "ATTACHMENTS/scan.pdf"), ("T/Hub.md", "pic.png"),
            ("T/Hub.md", "templates/Note Template")])
        self.assertEqual({t for _, t in result["edges"]}, result["incoming"])

    def test_link_targets(self):
        sys.path.insert(0, str(LINT_LINKS.parent))
        import lint_links
        text = "[[A|x]] [[B\\|y]] [[C#h]] [[ ]] `[[D]]`\n```\n[[E]]\n```\n[[F/G]]"
        self.assertEqual(lint_links.link_targets(text), ["A", "B", "C", "F/G"])


if __name__ == "__main__":
    unittest.main()
