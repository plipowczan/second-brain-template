import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LINT_LINKS = Path(__file__).resolve().parent / "lint_links.py"


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


if __name__ == "__main__":
    unittest.main()
