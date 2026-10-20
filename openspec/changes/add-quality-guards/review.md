# Review record — add-quality-guards

## Round 1 — 2026-10-20 — reviewed 378ef15

| id | sev | where | finding | outcome |
|---|---|---|---|---|
| R1-1 | P2 | .claude/skills/brain-lint/scripts/lint_scan.py:98-100 | A trailing YAML comment on `source:`/`sources:` hides quoted paths and flow lists from the missing-source check, and the `AGENTS.template.md` frontmatter example writes exactly such a commented flow list | fixed in 35f491b |

Test changes:
- `.claude/skills/brain-lint/scripts/test_lint_scan.py` — R1-1: new tests only (commented scalar, quoted scalar, flow list and block list; a `#` inside quotes or a URL fragment kept; an apostrophe in a plain scalar; a scan that reports commented missing paths). No existing assertion changed.

Checks: `python tests/run_tests.py` — ALL PASS; `python tests/run_skill_tests.py` — ALL PASS (305 tests, 0 skipped; brain-lint 32); `build_indexes.py` + `lint_scan.py` from the repo root — `git diff content/_indexes` showed only `updated:` lines.

## Round 2 — 2026-10-20 — reviewed e554067

| id | sev | where | finding | outcome |
|---|---|---|---|---|
| R2-1 | P2 | .claude/skills/brain-lint/scripts/lint_scan.py:27-53 (`parse_fm`, read by `source_values`) | An indentless block list (`sources:` then `- _raw/...`, valid YAML and PyYAML's default dump) parses as an empty field, so its sources are never checked | fixed in 6b30048 |
| R2-2 | P2 | .claude/skills/brain-lint/scripts/lint_scan.py:195-208 (`contradiction_count`) | Only three fence characters are stored, so a triple-backtick line closes a four-backtick block: examples inside it count as markers and later real markers are missed | fixed in 6b30048 |

Test changes:
- `.claude/skills/brain-lint/scripts/test_lint_scan.py` — R2-1: new tests only, for R2-1 and R2-2 (an indentless `tags:` and `sources:` list parsed, scanned and checked for missing paths; an unindented item after a scalar value left alone; a four-backtick block holding triple-backtick examples; a fence that closes only on the same character with no info string). No existing assertion changed.

Checks: `python tests/run_tests.py` — ALL PASS; `python tests/run_skill_tests.py` — ALL PASS (312 tests, 0 skipped; brain-lint 39); `build_indexes.py` + `lint_scan.py` from the repo root — `git diff content/_indexes` showed only `updated:` lines.
