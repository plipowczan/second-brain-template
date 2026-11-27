# Proposal

## Why

The template is good at putting knowledge into a base and bad at giving anything back.
Nothing comes back to the owner until they ask a question: no record of what the agent
did, no look back over a week, no sign of whether the link graph grows or decays, no way
to check what they themselves remember. A comparison with `undefined-ui/second-brain-os`
(MIT, read 2026-11-04) showed how to close that loop. Paweł accepted six points from it
on 2026-11-04 (`PL-665`), planned then as `0.4.0`; `0.4.0` and `0.4.1` shipped other work,
so this is the package for the next minor release, `0.5.0`.

The same release carries five small findings of the `v0.2.1` update pilot (bugs 7–11 of
`PL-481`), which `fix-upgrade-path` left for this package.

## What Changes

1. **Operation log.** Every skill that writes or moves notes appends one line to
   `content/_outputs/log.md`: when, which operation, counts, the notes it touched. Lines
   are only ever appended. The first skill that needs the file creates it.
2. **Periodic review, `/b:review`.** A new `brain-review` skill looks back over a period
   (since the last review, or 7 days): what came in, where attention went, open
   contradictions, thin places, questions the base could not answer, and the change in
   the metrics. It ends with three moves for the next period, each a command with its
   target, and saves a report.
3. **Metrics over time.** A new script computes the share of orphan notes, links per
   note, islands, isolated notes and notes untouched for 90 days, appends a dated
   snapshot to `content/_outputs/metrics.md` and compares it with the previous one. The
   review runs it. No pass or fail thresholds, only the trend (see design D6).
4. **Learning from your own notes, `/b:learn`.** A new `brain-learn` skill: a quiz drawn
   from the notes on a topic, and a Feynman session (the agent explains a note in plain
   words, the owner explains it back, the gaps are split into "the base lacks it", "its
   sources lack it" and "you missed it"). It saves the session and changes no note.
5. **Backlog ingest in batches.** `/b:ingest --backlog [N]` takes the N oldest sources in
   the inbox (10 by default), runs the normal ingest on them, and stops with the count
   left. The inbox is the checkpoint. No new command.
6. **A pattern for skill descriptions.** "Use when", one sentence on what it does and
   writes, "Do NOT use for" where a neighbouring skill overlaps, and in the body a
   "Calibration" section (the typical failure) and a fixed output shape. Applied to the
   two new skills and to `brain-ingest`; other skills adopt it when they next change.
7. **Upgrade fixes from the pilot.** The plan warns when an edited `.gitignore` still
   ignores `.kb-onboard.json` (bug 7). `commit` deletes the temporary folders of its
   plan, a `cleanup` step deletes those of `fetch`, nothing is deleted by pattern, and
   the tests leave none behind (bug 8).
   Without git, the backup folder always exists, lists the files the update added, and a
   new `undo` command restores the base from it (bug 9). The commit message names a
   local source by its file name, not its path (bug 10). Lint accepts the note types the
   owner chose at onboarding (bug 11).

No breaking change. Two new skills and two new commands, within the limit of three set on
2026-11-04.

## Capabilities

### New Capabilities

- `operation-log`: the append-only log, who writes it and what a line may contain.
- `periodic-review`: `/b:review`, its period, inputs, report and three moves.
- `vault-metrics`: the metrics, their snapshot file and the comparison.
- `learning-sessions`: `/b:learn`, quiz and explain-back, what is saved.
- `ingest-backlog`: `--backlog`, its order, batch size, checkpoint and skips.
- `skill-descriptions`: the description pattern and where it is checked.
- `onboarding-note-types`: note types chosen at onboarding are valid for lint.

`ingest-plan` and `lint-report` live in `add-quality-guards`, which is complete but not
archived, so `openspec/specs/` has nothing to modify for ingest or lint. As in
`slim-qa-navigation` (D3 there), this change adds new capabilities instead.

### Modified Capabilities

- `template-upgrade`: the backup without git, `undo`, temporary folders, the commit
  message, the `.gitignore` warning.

## Impact

- **New skills:** `.claude/skills/brain-review/`, `.claude/skills/brain-learn/`, their
  commands in `.claude/commands/b/`, their Codex stubs.
- **Scripts:** `brain-reindex/scripts/oplog.py` (new), `brain-lint/scripts/metrics.py`
  (new), `brain-lint/scripts/lint_links.py` (rewritten as functions behind golden
  tests, output unchanged), `brain-lint/scripts/lint_scan.py` (note types),
  `brain-ingest/scripts/inbox_order.py` (new), `brain-review/scripts/review_data.py`
  (new), `brain-upgrade/scripts/` (`upgrade.py`, `planner.py`, `sources.py`), tests.
- **Skills edited:** `brain-ingest` (backlog, log step, description pattern),
  `brain-compile`, `brain-enhance`, `brain-curate`, `brain-refactor`, `brain-import`,
  `brain-watch` (log step only), `brain-upgrade` (cleanup, undo, `.gitignore` step),
  `brain-lint` (`bad_type` advice).
- **Templates and docs:** `AGENTS.template.md` (four folder rows, two Workflows
  entries), `README.md` (two command rows, new bases only), `.gitattributes`
  (`merge=union` for the log and the metrics), `CONTRIBUTING.md` (the description
  pattern), `dev/build_codex_files.py` (description length check), `CHANGELOG.md`.
- **Existing bases:** everything arrives through `/b:upgrade`; the log, the metrics file
  and the learning folder are created on first use, because `content/` is seeded once.
- **Not in this repository:** the course cheat sheet and lessons (the parent session
  writes them from the text in the final report).
