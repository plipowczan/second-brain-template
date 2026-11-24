# Tasks

The change follows `CONTRIBUTING.md`: a `CHANGELOG.md` entry under `## [Unreleased]` in
the same commit (`origin/main` has no such heading yet, so this change adds it above
`## [0.4.1]`), and `python tests/run_tests.py` ends with `ALL PASS`. Public repository:
only aggregate figures from the measurement, no questions, note titles or paths of the
measured base.

## 1. brain-qa skill

- [x] 1.1 Apply the measured diff to `.claude/skills/brain-qa/SKILL.md` (steps 1 to 4
  rewritten, step 6 rewritten, step 7 points to step 1). Verify that the file before the
  change is the measured "before" and the result is the measured "after".
- [x] 1.2 Replace the pattern example in step 1 with a neutral one of the same build
  (design D2). Verify that this is the only line that differs from the measured text.
- [x] 1.3 Verify that the frontmatter did not change: `python dev/build_codex_files.py
  --check` passes and writes nothing.

## 2. `/b:qa` command

- [x] 2.1 Apply the measured diff to `.claude/commands/b/qa.md`: the new instruction and
  the file reference `@.claude/skills/brain-qa/SKILL.md` with an ASCII `@`. Verify that
  the result is the measured "after".

## 3. Agent instructions

- [x] 3.1 In `AGENTS.template.md`, carry the measured sentences into the Navigation
  Protocol (design D1): Level 0 and Level 1 headers, the Level 1 and Level 2 sentences,
  rules 1, 2, 4 and 5. Verify by rendering the file with
  `brain-onboard/scripts/render.py` and a temporary values file: the output holds the new
  rules and no unresolved `{{`.

## 4. Changelog and checks

- [x] 4.1 Add `## [Unreleased]` and a `Changed` entry for base owners: what changes in
  the cost of a question, with the aggregate figures, and what an existing base does.
- [x] 4.2 `openspec validate slim-qa-navigation --strict` passes.
- [x] 4.3 `python tests/run_tests.py` ends with `ALL PASS`.
- [x] 4.4 Open a pull request into `main` with the before/after table in its description.
  The maintainer merges it.
