# Tasks

The change follows `CONTRIBUTING.md`: every commit that changes behaviour carries its
`CHANGELOG.md` entry under `## [Unreleased]`, `python tests/run_tests.py` and
`python tests/run_skill_tests.py` pass, also on Windows with Python 3.11 (no function
newer than 3.11 without a fallback), and `python dev/build_codex_files.py` runs after
every skill frontmatter change. Public repository: only aggregate figures from the
maintainer's base, no titles, folders or paths from it.

## 1. Operation log

- [ ] 1.1 `brain-reindex/scripts/oplog.py append` with tests: creates the file with its
  header, appends one LF row in one write, builds "What" from `--count key=N` only, lists
  at most 10 `--note` paths as code spans then "and N more", escapes `|`, refuses free
  text, leaves hand-written lines alone.
- [ ] 1.2 `.gitattributes`: `content/_outputs/log.md merge=union` and
  `content/_outputs/metrics.md merge=union`. Test: two branches that each append a row
  merge without a conflict.
- [ ] 1.3 One log step in `brain-ingest`, `brain-compile`, `brain-enhance`,
  `brain-curate`, `brain-refactor`, `brain-import`, `brain-watch`: after a run that wrote,
  moved or retired a note, never after a cancelled or empty run.
- [ ] 1.4 Verify in a scratch vault that indexes, `lint_scan.py`, `lint_links.py`, the
  pre-commit hook and `/b:export --public` ignore the log.

## 2. Metrics

- [ ] 2.1 Make `lint_links.py` importable (walk and resolution in functions, a `main()`),
  with a test that pins its printed output on a fixture vault to the output before the
  change.
- [ ] 2.2 `brain-lint/scripts/metrics.py` with tests: the six metrics, last touch with
  its basis (git and frontmatter), `--record` creating `content/_outputs/metrics.md`,
  replacing the same day's row, comparing with the latest earlier day, "not comparable"
  across bases, no write without `--record`, a note with no links counted as isolated.
- [ ] 2.3 Test that `metrics.py` and `lint_links.py` report the same orphans on the same
  vault.

## 3. Review

- [ ] 3.1 `brain-review/scripts/review_data.py` with tests: period start (log row, report
  file, 7 days, `--since`, `--days`), log rows and touched folders, answers and learning
  sessions in the period, git changes in the period, inbox count, the three subprocess
  outputs merged, a vault without git, an empty log.
- [ ] 3.2 `.claude/skills/brain-review/SKILL.md` in the description pattern: inputs,
  report shape, the order of the three moves, the call-out steps of design D6, below 10
  notes stop, no questions, one `review` log row.
- [ ] 3.3 `.claude/commands/b/review.md`.

## 4. Learning

- [ ] 4.1 `.claude/skills/brain-learn/SKILL.md` in the description pattern: explain-back
  with the three kinds of gap, `--quiz [N]`, the session file, no note written, stop
  without a person.
- [ ] 4.2 `.claude/commands/b/learn.md`.

## 5. Backlog ingest

- [ ] 5.1 `brain-ingest/scripts/inbox_order.py` with tests: the order (date in name,
  frontmatter `date:`, modification time, name), the first N, and duplicates of
  `_raw/processed/` by content hash.
- [ ] 5.2 `brain-ingest/SKILL.md`: `--backlog [N]`, the automatic batches above 10
  sources, `--backlog` with `--batch`, skips to `_raw/skipped/`, the closing count, the
  argument check accepting `--backlog` and its number.

## 6. Skill descriptions

- [ ] 6.1 `CONTRIBUTING.md`: the pattern (design D10).
- [ ] 6.2 `dev/build_codex_files.py --check` fails on a description over 500 characters,
  with a test.
- [ ] 6.3 Apply the pattern to every skill edited in sections 1, 3, 4, 5 and 7, and add
  "Do NOT use for" to `brain-lint`, `brain-gaps` and `brain-qa` against the new skills.
  Run `python dev/build_codex_files.py` and commit the stubs.

## 7. Upgrade fixes (bugs 7–11)

- [ ] 7.1 Bug 7: plan warning when `.kb-onboard.json` will be tracked and `git
  check-ignore` matches it, naming the rule; the skill's step that offers the extra
  commit. Test with an edited `.gitignore`.
- [ ] 7.2 Bug 8: the plan records its temporary folders; `commit` and `apply` without git
  delete them; `fetch` prints its folders; `cleanup --path` with its guard. Tests: a
  parallel plan's folders survive, a folder outside the temp directory is refused, a
  failed step keeps its folders, and the test suites leave no `kb-upgrade-*` folder.
- [ ] 7.3 Bug 9: the backup folder always created without git, `backup.json`, `undo
  --backup` in one transaction; adoption names the folder only when it exists. Tests:
  adoption that only adds, undo after an upgrade, an added file edited after apply, a
  link in the path, an invalid `backup.json`.
- [ ] 7.4 Bug 10: the commit body names a zip, folder or clone by its last path
  component. Test with a zip source.
- [ ] 7.5 Bug 11: `lint_scan.py` accepts `NOTE_TYPES` from `.kb-onboard.json` without
  required fields; the `bad_type` advice in `brain-lint/SKILL.md`. Tests: own type,
  unknown type, missing values file.
- [ ] 7.6 `brain-upgrade/SKILL.md`: the cleanup step, `undo`, the `.gitignore` offer.

## 8. Templates, docs, release notes

- [ ] 8.1 `AGENTS.template.md`: rows for `_outputs/log.md`, `_outputs/metrics.md`,
  `_outputs/learning/`.
- [ ] 8.2 `README.md`: rows for `/b:review` and `/b:learn`, `--backlog` in the
  `/b:ingest` row.
- [ ] 8.3 `CHANGELOG.md` under `[Unreleased]`: one entry per behaviour, each with
  "Existing bases", the inspiration from `undefined-ui/second-brain-os` (MIT) named once.
- [ ] 8.4 `python tests/run_tests.py` and `python tests/run_skill_tests.py` green locally
  on Windows with the newest Python and with Python 3.11.

## 9. Trial and pull request

- [ ] 9.1 Trial on a fresh copy of the maintainer's base in a temporary folder (never the
  base itself): upgrade or port, `/b:review`, `/b:learn --quiz`, `/b:ingest --backlog`,
  the log rows, the metrics file; record the result in the pull request.
- [ ] 9.2 Pull request; Codex review run and every finding resolved; CI green.
