# Review record — add-quality-guards

## Round 1 — 2026-10-20 — reviewed 378ef15

| id | sev | where | finding | outcome |
|---|---|---|---|---|
| R1-1 | P2 | .claude/skills/brain-lint/scripts/lint_scan.py:98-100 | A trailing YAML comment on `source:`/`sources:` hides quoted paths and flow lists from the missing-source check, and the `AGENTS.template.md` frontmatter example writes exactly such a commented flow list | fixed in 35f491b |

Test changes:
- `.claude/skills/brain-lint/scripts/test_lint_scan.py` — R1-1: new tests only (commented scalar, quoted scalar, flow list and block list; a `#` inside quotes or a URL fragment kept; an apostrophe in a plain scalar; a scan that reports commented missing paths). No existing assertion changed.

Checks: `python tests/run_tests.py` — ALL PASS; `python tests/run_skill_tests.py` — ALL PASS (305 tests, 0 skipped; brain-lint 32); `build_indexes.py` + `lint_scan.py` from the repo root — `git diff content/_indexes` showed only `updated:` lines.
