# Spec Delta

## Purpose

Defines the link and freshness metrics of a vault, the dated snapshots that make them a
trend, and when a change is called out.

## ADDED Requirements

### Requirement: Metrics use the definitions of lint

`brain-lint/scripts/metrics.py` SHALL compute `notes`, `orphans`, `isolated`, `weak`,
`links_per_note`, `islands` and `untouched_90d` from the notes themselves, with the note
set, link resolution and orphan rule of `lint_links.py`, by importing it.
`links_per_note` SHALL count distinct links from a note to another note. With no notes,
every share and average SHALL be `null`.

#### Scenario: Same orphan count in lint and review
- **WHEN** `/b:lint` and `/b:review` run on the same vault
- **THEN** both report the same number of orphans

#### Scenario: Note without any link
- **WHEN** a note has no link to or from another note
- **THEN** it is counted in `notes`, `orphans`, `isolated` and `weak`, whether or not `graph.md` is current

### Requirement: lint_links keeps its output

`lint_links.py` SHALL expose its walk and link resolution as functions that also return
the edges between notes, and, run as a script, SHALL print exactly what it printed before
this change. Tests SHALL pin that output on a fixture vault before the rewrite.

#### Scenario: Script run after the rewrite
- **WHEN** `lint_links.py` runs on the fixture vault
- **THEN** its output equals the output recorded from the code before the change

### Requirement: Last touch has one definition and a recorded basis

A note's last touch SHALL be the latest of its frontmatter `date`, its `agent-reviewed`
and, in a git base, its last commit, read in one `git log -z` call for the vault. Each
snapshot SHALL record its basis, `git` or `frontmatter`, and a comparison between
snapshots of different bases SHALL report `untouched_90d` as not comparable.

#### Scenario: Base without git
- **WHEN** the vault is not a git repository
- **THEN** last touch comes from the frontmatter and the snapshot's basis is `frontmatter`

### Requirement: Snapshots are dated rows, one per day

`metrics.py --record` SHALL add the snapshot as one row of `content/_outputs/metrics.md`,
creating the file with its header on first use, and SHALL replace the row of the same
UTC day. Reading the file it SHALL take the last row per date and sort rows by date. It
SHALL print the snapshot, the comparison snapshots and the differences as JSON. Without
`--record` it SHALL write nothing.

#### Scenario: Union merge left two rows for one day
- **WHEN** the file holds two rows dated the same day in merge order
- **THEN** the later row counts and the comparison is unaffected

### Requirement: A metric is called out only when it worsened

The review SHALL compare a snapshot with the previous one and with the newest one at least
28 days old, and SHALL call out a metric only when it got worse in either comparison by at
least: `orphans` or `isolated` +2 percentage points and at least 2 more notes, `islands`
+1, `links_per_note` −0.5, `untouched_90d` +5 percentage points and at least 2 more notes.
Below 30 notes it SHALL call out none. No metric SHALL be judged against an absolute
target.

#### Scenario: First snapshot
- **WHEN** there is no earlier snapshot
- **THEN** the review shows the values and calls none out

#### Scenario: One new orphan in a 40-note base
- **WHEN** orphans go from 4 to 5 of 40 notes
- **THEN** nothing is called out, because only one note more is an orphan
