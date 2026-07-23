import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render  # noqa: E402


class TestSubstitute(unittest.TestCase):
    def test_simple_substitution(self):
        self.assertEqual(render.render("Hello {{NAME}}", {"NAME": "World"}), "Hello World")

    def test_multiple_vars(self):
        out = render.render("{{A}}-{{B}}-{{A}}", {"A": "x", "B": "y"})
        self.assertEqual(out, "x-y-x")

    def test_non_string_value_coerced(self):
        self.assertEqual(render.render("n={{N}}", {"N": 3}), "n=3")

    def test_missing_var_raises(self):
        with self.assertRaises(render.RenderError):
            render.render("Hello {{MISSING}}", {"NAME": "x"})


class TestConditionals(unittest.TestCase):
    def test_if_true_keeps_block(self):
        tmpl = "a<!-- IF:flag -->B<!-- /IF:flag -->c"
        self.assertEqual(render.render(tmpl, {"flag": True}), "aBc")

    def test_if_false_drops_block(self):
        tmpl = "a<!-- IF:flag -->B<!-- /IF:flag -->c"
        self.assertEqual(render.render(tmpl, {"flag": False}), "ac")

    def test_false_block_with_unknown_var_is_safe(self):
        tmpl = "x<!-- IF:flag -->{{GONE}}<!-- /IF:flag -->y"
        self.assertEqual(render.render(tmpl, {"flag": False}), "xy")

    def test_missing_flag_raises(self):
        with self.assertRaises(render.RenderError):
            render.render("<!-- IF:flag -->z<!-- /IF:flag -->", {})

    def test_multiline_block(self):
        tmpl = "head\n<!-- IF:on -->\nline1\nline2\n<!-- /IF:on -->\ntail"
        out = render.render(tmpl, {"on": True})
        self.assertIn("line1", out)
        self.assertIn("line2", out)
        self.assertNotIn("IF:on", out)


class TestCli(unittest.TestCase):
    def test_cli_renders_file(self):
        here = Path(__file__).resolve().parent
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "t.md").write_text("Hi {{NAME}}", encoding="utf-8")
            (d / "v.json").write_text(json.dumps({"NAME": "Ada"}), encoding="utf-8")
            out = d / "out.md"
            r = subprocess.run(
                [sys.executable, str(here / "render.py"),
                 "--template", str(d / "t.md"),
                 "--values", str(d / "v.json"),
                 "--out", str(out)],
                capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(out.read_text(encoding="utf-8"), "Hi Ada")

    def test_cli_missing_var_exits_nonzero(self):
        here = Path(__file__).resolve().parent
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "t.md").write_text("Hi {{MISSING}}", encoding="utf-8")
            (d / "v.json").write_text("{}", encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(here / "render.py"),
                 "--template", str(d / "t.md"),
                 "--values", str(d / "v.json"),
                 "--out", str(d / "out.md")],
                capture_output=True, text=True,
            )
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("MISSING", r.stderr)


if __name__ == "__main__":
    unittest.main()
