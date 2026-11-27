# Spec Delta

## Purpose

Defines the link and freshness metrics of a vault, the dated snapshots that make them a
trend, and how a snapshot is compared with the one before.

## ADDED Requirements

### Requirement: Metrics use the definitions of lint

`brain-lint/scripts/metrics.py` SHALL compute `notes`, `orphans`, `isolated`,
`links_per_note`, `islands` and `untouched_90d` from the notes themselves, with the note
set, link resolution and orphan rule of `lint_links.py`, by importing it. `lint_links.py`
run as a script SHALL print the same output as before this change.

#### Scenario: Same orphan count in lint and review
- **WHEN** `/b:lint` and `/b:review` run on the same vault
- **THEN** both report the same number of orphans

#### Scenario: Note without any link
- **WHEN** a note has no link in or out
- **THEN** it is counted in `notes`, `orphans` and `isolated`, whether or not `graph.md` is current

### Requirement: Last touch has one definition and a recorded basis

A note's last touch SHALL be the latest of its frontmatter `date`, its `agent-reviewed`
and, in a git base, its last commit. Each snapshot SHALL record its basis, `git` or
`frontmatter`, and a comparison between snapshots of different bases SHALL report
`untouched_90d` as not comparable.

#### Scenario: Base without git
- **WHEN** the vault is not a git repository
- **THEN** last touch comes from the frontmatter and the snapshot's basis is `frontmatter`

### Requirement: Snapshots are dated rows, one per day

`metrics.py --record` SHALL add the snapshot as one row of `content/_outputs/metrics.md`,
creating the file with its header on first use, and SHALL replace the row of the same
UTC day when there is one. It SHALL print, as JSON, the snapshot, the latest snapshot of
an earlier day (or none) and the difference per metric. Without `--record` it SHALL write
nothing.

#### Scenario: Second review on the same day
- **WHEN** the review runs twice on one day
- **THEN** the file holds one row for that day and the comparison is with the previous day that has a row

### Requirement: A metric is called out only when it worsened

The review SHALL call out a metric only when, compared with the previous snapshot, it got
worse by at least: orphans +2 percentage points, isolated +2 points, islands +1, links per
note −0.5, untouched for 90 days +5 points. Below 30 notes it SHALL call out none. No
metric SHALL be judged against an absolute target.

#### Scenario: First snapshot
- **WHEN** there is no earlier snapshot
- **THEN** the review shows the values and calls none out
