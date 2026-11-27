---
name: brain-review
description: 'Use when the user says "review", "weekly review", "what changed in my vault", "przegląd", or a schedule runs `/b:review`. Reports what came in since the last review, open contradictions, thin places, unanswered questions and the metrics with their trend, and ends with three moves; writes one report to `_outputs/reports/` and one log row, never a note. Do NOT use for a health audit (use `/b:lint`) or coverage analysis (use `/b:gaps`).'
---

# REVIEW

## When to use

The owner wants to know what happened in the base since the last review and what to do
next: typically once a week. The review asks nothing, so it can also run from a
schedule with no person present. It is not a health audit: `/b:lint` lists every
mechanical problem, `/b:gaps` maps what is missing; the review reads the period and
picks three moves.

Arguments: `--since YYYY-MM-DD` (a UTC date) or `--days N` set the period. Without
them the period starts at the last review.

## Workflow

1. **Gather the data** from the vault root, passing the arguments through:

   ```bash
   python .claude/skills/brain-review/scripts/review_data.py [--since YYYY-MM-DD | --days N]
   ```

   It prints one JSON object: `period`, `notes`, `too_young`, `log`, `recent_changes`,
   `answers`, `learning`, `git`, `inbox`, `contradictions`, `metrics`, `thin`,
   `unavailable` and `report_path`. It also records today's metrics in
   `content/_outputs/metrics.md` (one row per day; a second run on the same day
   replaces it). Work from this JSON; do not search the vault for the same facts.
2. **Too young.** When `too_young` is true, tell the user the base has `notes` notes,
   too few for a review (the same floor of 10 as `/b:lint`), and stop: no report, no
   log row.
3. **Read only what a move needs.** For each note you are about to name in a move,
   read that note (for a contradiction, the callout) so the move says what to decide or
   add. Read nothing else.
4. **Write the report** to `report_path`, the next free name in
   `content/_outputs/reports/` (`YYYY-MM-DD_review.md`, then `-2`, `-3`; an earlier
   report is never overwritten), in the shape below and in the vault's primary language
   from the writing-style document (`content/WRITING_STYLE.md`, or the one AGENTS.md
   "Writing Style" names in an older base).
5. **Log the run** (one row; `days` is the length of the period, so the next review
   knows where this one started):

   ```bash
   python .claude/skills/brain-reindex/scripts/oplog.py append --op review --count days=<period.days> --note <report_path without content/ and .md>
   ```

   When `oplog.py` is missing, skip the row and say so in the closing message.
6. **Tell the user** in the closing message shape below.

## Report shape

```markdown
---
title: "<Review, in the vault language> YYYY-MM-DD"
date: YYYY-MM-DD
type: review-report
summary: "<the period and the first move, in one line>"
agent-created: true
---

# <title>

<period: since … until …, N days>

## What came in
## Where attention went
## Open contradictions
## Thin places
## Questions the base could not answer
## Metrics
## Three moves
```

The headings are in the vault language. What each section holds:

- **What came in.** From `log.by_op`: runs and counts per operation (`ingest: 2 runs,
  5 sources, 3 notes created, 7 updated`). From `recent_changes`: the entries dated in
  the period, at most five (say how many more). From `git`: commits in the period and
  the number of notes they created or changed (`git.created_count`,
  `git.changed_count`); `git.uncommitted` as "new or changed, not committed yet". When
  `git.available` is false (no git, no commit yet, or a shallow clone, whose history
  stops at the graft), leave git out and rely on the other sources; a shallow clone is
  also in `unavailable`. From `inbox`: the sources waiting, and how many of them are
  unusable or duplicates of an archived source. Both ends of the period are included,
  so the day of the last review counts in both reviews. When `log.rows` is empty, say
  that the log has no rows for the period (a base fresh from an upgrade, or skills the
  owner kept at their own version, write none) and rely on the other sources.
- **Where attention went.** `log.folders` and `git.folders`, the counts of one folder
  added up, most touched first, at most five.
- **Open contradictions.** The number of notes and of callouts in `contradictions`, then
  at most five notes, those in a folder of this period first, then the fewest callouts
  first (one decision closes such a note). These stay open until the owner decides which
  claim holds.
- **Thin places.** First `thin.in_touched_folders` (orphans, isolated and weak notes in
  the folders of this period), then the totals from `metrics.snapshot` and the number of
  `islands`. At most five notes by name.
- **Questions the base could not answer.** Every saved answer in `answers` and every
  learning session in `learning` with `gaps` above zero (for a session, `gaps` counts
  what the base or its sources lack): its title, the count and a wikilink to the file.
  A session whose `missed` is above zero but whose `gaps` is zero goes here only as one
  line: the owner missed points the notes have.
- **Metrics.** A table: metric · now · previous (`metrics.previous.date`) · change ·
  four or more weeks ago (`metrics.older.date`) · change, for `notes`, `orphans`,
  `isolated`, `weak`, `links_per_note`, `islands` and `untouched_90d` (shares as
  percentages, with the count). Under the table, each entry of `metrics.callouts` as one
  sentence, with `from_pct` and `to_pct` where it has them ("orphans rose from 4.1 % to
  6.5 % since 2026-11-20"); a metric called out against both snapshots gets one
  sentence. Where a snapshot exists and `metrics.comparable` is false for it, write "not
  comparable" for `untouched_90d` (the two snapshots measured last touch differently).
  With `metrics.previous` null, say that this is the first measurement and the trend
  starts at the next review. Never call a metric good or bad by its value alone: only a
  callout says that something got worse.
- **Three moves.** See below.

An empty section says in one line that nothing happened there. A part listed in
`unavailable` says so in its section, with the reason (for example, the metrics script
is missing because the owner deleted `brain-lint`).

## Three moves

Each move is one command or one action with its target, which the owner can run as it
stands:

- `decide which claim holds in [[Note]]: <the two claims in a few words>` (for a note
  with several callouts, name the subject of the first and how many there are); pick
  the note as in Open contradictions
- `/b:compile <subject>` or `drop a source on <subject> into the inbox`, for an
  unanswered question
- `/b:enhance [[Note]]`, for an orphan, isolated or weak note
- `/b:ingest --backlog`, for a waiting inbox (`inbox.sources` above zero)
- `/b:enhance [[Note]]` or `/b:curate`, for an untouched note

Take candidates in this order: an open contradiction, an unanswered question, an orphan
or weak note in a folder the owner worked in this period, a waiting inbox, an untouched
note. Use at most two moves of one kind. With fewer than three candidates, give fewer
moves and say that there was nothing more to suggest.

## Calibration

A review goes wrong when it turns into a lint report (every orphan listed), when it
reads trend into a single snapshot, or when its moves are advice ("improve linking")
instead of commands. Right: every number comes from the JSON, no list is longer than
five entries, a trend is named only against a recorded snapshot, and each of the three
moves can be run as written.

## Closing message

```
Review <since> – <until> (<days> days): <path of the report>
Moves:
1. <move>
2. <move>
3. <move>
<one line per callout; "No metric got worse." when there are none; "First
measurement: the trend starts at the next review." when metrics.previous is null>
<one line per unavailable part, if any>
```

Ask nothing. The report is not committed by this skill; it is a file in
`_outputs/reports/`, like the lint report.

## See also

CLAUDE.md "Navigation Protocol". `LIMITS.md` before saying the base is in good shape:
a quiet review means nothing got worse, not that the notes are true.
