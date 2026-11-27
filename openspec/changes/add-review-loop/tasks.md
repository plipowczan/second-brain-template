# Tasks

The change follows `CONTRIBUTING.md`: every commit that changes behaviour carries its
`CHANGELOG.md` entry under `## [Unreleased]`, `python tests/run_tests.py` and
`python tests/run_skill_tests.py` pass, also on Windows with Python 3.11 (no function
newer than 3.11 without a fallback; `shutil.rmtree` without `onexc`), and
`python dev/build_codex_files.py` runs after every skill frontmatter change. Public
repository: only aggregate figures from the maintainer's base, no titles, folders or
paths from it.

## 1. Operation log

- [x] 1.1 `brain-reindex/scripts/oplog.py append` with tests: creates the file with its
  header; adds a missing final newline; appends one row as bytes with LF in one write;
  "What" only from `key=N` tokens (refuses anything else); at most 10 `--note` paths as
  code spans then "and N more"; `|` escaped; private terms masked as `[private]` through
  `brain-export/scripts/privacy_sweep.py`, and a stderr notice when that script is
  missing; hand-written lines left alone.
- [x] 1.2 `.gitattributes`: `content/_outputs/log.md merge=union` and
  `content/_outputs/metrics.md merge=union`. Test: two branches that each create and
  append merge without a conflict.
- [x] 1.3 One log step in `brain-ingest`, `brain-compile`, `brain-enhance`,
  `brain-curate`, `brain-refactor`, `brain-import`, `brain-watch`: after a run the owner
  started that wrote, moved or retired a note; none after a cancelled or empty run, and
  none when the skill runs inside another skill (curate handing work to refactor or
  enhance).
- [x] 1.4 Verify in a scratch vault that indexes, `lint_scan.py`, `lint_links.py`, the
  pre-commit hook and `/b:export --public` ignore the log, the metrics file and
  `_outputs/learning/`.

## 2. Metrics

- [x] 2.1 Golden-output tests for `lint_links.py` on a fixture vault (self-links, links in
  code, attachments, `templates/`, broken links, duplicate basenames, non-ASCII names),
  recorded from the code as it is now.
- [x] 2.2 Rewrite `lint_links.py` as functions that return notes, resolved note-to-note
  edges, attachment and template links, and broken links; `main()` prints the same output.
  The golden tests pass unchanged.
- [x] 2.3 `brain-lint/scripts/metrics.py` with tests: the seven metrics (distinct
  note-to-note links, `weak` at most one distinct link, `null` for an empty vault); last
  touch from one `git log -z` call and from frontmatter, with its basis; `--record`
  creating `content/_outputs/metrics.md`, replacing the same day's row; reading the last
  row per date, sorted; comparison with the previous snapshot and with the newest one at
  least 28 days old; "not comparable" across bases; no write without `--record`.
- [x] 2.4 Test that `metrics.py` and `lint_links.py` report the same orphans on the same
  vault.

## 3. Review

- [x] 3.1 `brain-review/scripts/review_data.py` with tests: period start (review row with
  `days=N`, same-day re-run, report file, 7 days, `--since` as a UTC date, `--days`); log
  rows sorted by time and touched folders; `## Recent Changes` entries in the period;
  answers and learning sessions filtered by date; git commits and uncommitted changes
  (`-z`, non-ASCII paths); inbox count; `lint_scan.py` and `metrics.py --record` as
  subprocesses; a missing or failing script reported as unavailable; a vault without git;
  an empty log.
- [x] 3.2 Call-out rules of design D6 (steps, at least 2 notes, two comparisons, none
  below 30 notes) as a function with tests, used by `review_data.py`.
- [x] 3.3 `.claude/skills/brain-review/SKILL.md` in the description pattern: inputs,
  report shape and file name (never overwritten), the order of the three moves, below
  10 notes stop, no questions, one `review` row with `days=N`.
- [x] 3.4 `.claude/commands/b/review.md`.

## 4. Learning

- [x] 4.1 `.claude/skills/brain-learn/SKILL.md` in the description pattern: explain-back
  with the three kinds of gap, `--quiz [N]`, the session file (slug checked against
  private terms, never overwritten, committed like answers and said so on the first
  run), offers instead of writes, stop without a person.
- [x] 4.2 `.claude/commands/b/learn.md`.

## 5. Backlog ingest

- [x] 5.1 `brain-ingest/scripts/inbox_order.py` with tests: sources and attachments
  told apart; the order (date in the name, frontmatter `date:`, modification time,
  name); empty and unreadable files listed apart; content equal to a file in
  `_raw/processed/` (SHA-256).
- [x] 5.2 `brain-ingest/SKILL.md` in the description pattern: `--backlog [N]` (every URL
  argument, then the inbox up to N), the automatic batches above 10 sources, `--backlog`
  with `--batch`, skips to `_raw/skipped/` in interactive runs only, unusable files named
  in every report, the closing count in place of "Inbox now empty.", the argument rule and
  its row in the failure table. Description stays under 500 characters.

## 6. Skill descriptions

- [x] 6.1 `CONTRIBUTING.md`: the pattern (design D10) and the rule that an existing
  skill adopts it when it is next changed for a reason of its own.
- [x] 6.2 New: `dev/build_codex_files.py --check` fails on a description over 500
  characters and names the skill and the length; test.
- [x] 6.3 Run `python dev/build_codex_files.py` and commit the stubs for the new and
  changed skills.

## 7. Upgrade fixes (bugs 7–11)

- [x] 7.1 Bug 7: plan warning when `.kb-onboard.json` will be tracked and
  `git check-ignore -v` matches it, naming the rule; the skill's step that offers the
  extra commit. Test with an edited `.gitignore`.
- [x] 7.2 Bug 8: `commit` deletes the folder of the plan and its payload as its last
  step, git or not, and keeps the download; `apply` and failed steps delete nothing;
  `plan` and `fetch` print their folders; `cleanup --path` and every deletion check the
  temp parent, the prefix and links. Tests: a merge still finds the payload after apply,
  the download survives `commit` (offline cycle after an adoption), a parallel plan's
  folders survive, a folder outside the temp directory or behind a junction is refused,
  a failed step keeps its folders; every suite sets `TMP`, `TEMP` and `TMPDIR` to a
  `TemporaryDirectory`, and a check after the suites finds no new `kb-upgrade-*` folder.
- [x] 7.3 Bug 9: the backup folder always created without git; `backup.json` with the
  hash before and after of every path apply wrote or deleted; `undo --backup` (stamp must
  match, restore only on a matching hash, `content/WRITING_STYLE.md` allowed, nothing else
  under `content/`, no links, one transaction). Adoption names the folder only when it
  exists. Tests: adoption that only adds, undo after an upgrade, an added file edited
  after apply, the older of two backups refused, a re-rendered `WRITING_STYLE.md`, a link
  in the path, an invalid `backup.json`.
- [x] 7.4 Bug 10: the commit body names a zip, folder or clone by its last path
  component. Test with a zip source.
- [x] 7.5 Bug 11: `lint_scan.py` accepts `NOTE_TYPES` from `.kb-onboard.json` without
  required fields; the `bad_type` advice in `brain-lint/SKILL.md`. Tests: own type,
  unknown type, missing or broken values file.
- [x] 7.6 `brain-upgrade/SKILL.md`: the cleanup phase, `undo`, the `.gitignore` offer.

## 8. Templates, docs, release notes

- [x] 8.1 `AGENTS.template.md`: folder rows for `_outputs/log.md`, `_outputs/metrics.md`,
  `_outputs/learning/`, `_raw/skipped/`; Workflows entries REVIEW and LEARN.
- [x] 8.2 `README.md`: rows for `/b:review` and `/b:learn`, `--backlog` in the
  `/b:ingest` row (new bases only).
- [x] 8.3 `CHANGELOG.md` under `[Unreleased]`: one entry per behaviour, each with
  "Existing bases"; the inspiration from `undefined-ui/second-brain-os` (MIT) named
  once; the first-run steps of design D11 (delete the `fetch` folders, the `.gitignore`
  line, the `undo` command); edited skills write no log rows; learning sessions are
  committed; old log rows keep paths from before a rename.
- [ ] 8.4 `python tests/run_tests.py` and `python tests/run_skill_tests.py` green locally
  on Windows with the newest Python and with Python 3.11.

## 9. Trial and pull request

- [x] 9.1 Trial on a fresh copy of the maintainer's base in a temporary folder (never the
  base itself): bring the branch's skills in, then `/b:review`, `/b:learn --quiz`,
  `/b:ingest --backlog` on a few sources, the log rows, the metrics file; record the
  result in the pull request.
- [ ] 9.2 Pull request; Codex review run and every finding resolved; CI green.

## Follow-up (not in this change)

- Archive `add-quality-guards`, then archive this change with the argument rule of
  `ingest-backlog` rewritten as a MODIFIED delta of `ingest-plan` (design, "Archive
  order").
