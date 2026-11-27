# Spec Delta

## Purpose

Defines the append-only record of what the agent did to a base: where it lives, who
writes it, what a row may contain, and how it behaves without git and across clones.

## ADDED Requirements

### Requirement: Skills that write or move notes append one row per run

`brain-ingest`, `brain-compile`, `brain-enhance`, `brain-curate`, `brain-refactor`,
`brain-import` and `brain-watch` SHALL, after a run that wrote, moved or retired at least
one note, append exactly one row to `content/_outputs/log.md` by running
`brain-reindex/scripts/oplog.py append`. `brain-review` and `brain-learn` SHALL append one
row per completed run. A run that wrote nothing SHALL append no row.

#### Scenario: Ingest of three sources
- **WHEN** `/b:ingest` creates two notes and updates five from three sources
- **THEN** one row is appended, with the operation `ingest`, the counts and the paths of the seven notes

#### Scenario: Cancelled ingest
- **WHEN** the owner cancels at the plan
- **THEN** no row is appended

### Requirement: The log file is created on first use and only ever appended to

`oplog.py` SHALL create `content/_outputs/log.md` with its table header when the file is
missing, and SHALL otherwise only append. It SHALL write each row in one write with an LF
line ending, and SHALL NOT rewrite, reorder or truncate existing content.

#### Scenario: Base upgraded from 0.4.1
- **WHEN** a base that has no `content/_outputs/log.md` runs its first `/b:enhance` after the upgrade
- **THEN** the file is created with the header and one row

#### Scenario: Owner added a line by hand
- **WHEN** the file holds a line the owner wrote
- **THEN** the next row is appended after it and the owner's line is unchanged

### Requirement: A row holds counts and paths only

A row SHALL hold the UTC time, the operation name, a "What" cell built only from named
counts, and the paths of the notes or archived sources the run touched, as code spans, at
most ten followed by the number of the rest. It SHALL NOT hold quotes from sources, the
text of a question or answer, or any other free text. `|` in a path SHALL be escaped.

#### Scenario: Large run
- **WHEN** a run touched 14 notes
- **THEN** the row lists 10 paths and "and 4 more"

#### Scenario: Free text requested
- **WHEN** a skill passes text other than named counts and paths
- **THEN** `oplog.py` refuses with an error and appends nothing

### Requirement: The log merges and stays private like the outputs

`.gitattributes` SHALL mark `content/_outputs/log.md` and `content/_outputs/metrics.md`
with `merge=union`. Indexes, lint and `/b:export --public` SHALL keep skipping the file
as they skip the rest of `content/_outputs/`.

#### Scenario: Two clones appended rows
- **WHEN** two clones of a base each appended a row and one merges the other
- **THEN** git merges the file without a conflict and both rows are kept
