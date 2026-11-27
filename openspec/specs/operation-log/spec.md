# operation-log Specification

## Purpose
Defines the append-only record of what the agent did to a base: where it lives, who
writes it, what a row may contain, and how it behaves without git and across clones.

## Requirements

### Requirement: Skills that write or move notes append one row per run

`brain-ingest`, `brain-compile`, `brain-enhance`, `brain-curate`, `brain-refactor`,
`brain-import` and `brain-watch`, when run by the owner, SHALL append exactly one row to
`content/_outputs/log.md` after a run that wrote, moved or retired at least one note, by
running `brain-reindex/scripts/oplog.py append`. A skill run by another skill SHALL
append no row of its own. `brain-review` and `brain-learn` SHALL append one row per
completed run. A run that wrote nothing SHALL append no row.

#### Scenario: Ingest of three sources
- **WHEN** `/b:ingest` creates two notes and updates five from three sources
- **THEN** one row is appended, with the operation `ingest`, the counts and the paths of the seven notes

#### Scenario: Cancelled ingest
- **WHEN** the owner cancels at the plan
- **THEN** no row is appended

#### Scenario: Curate hands a merge to refactor
- **WHEN** `/b:curate` retires two notes and has `brain-refactor` merge two others
- **THEN** one `curate` row is appended and no `refactor` row

### Requirement: The log file is created on first use and only ever appended to

`oplog.py` SHALL create `content/_outputs/log.md` with its table header when the file is
missing, and SHALL otherwise only append: it SHALL add a final newline when the file
lacks one, then write the row as bytes with an LF ending in one write. It SHALL NOT
rewrite, reorder or truncate existing content.

#### Scenario: Base upgraded from 0.4.1
- **WHEN** a base that has no `content/_outputs/log.md` runs its first `/b:enhance` after the upgrade
- **THEN** the file is created with the header and one row

#### Scenario: Owner added a line without a final newline
- **WHEN** the file ends with a line the owner wrote and no newline
- **THEN** the next row starts on its own line and the owner's line is unchanged

### Requirement: A row holds counts and paths only

A row SHALL hold the UTC time, the operation name, a "What" cell made only of `key=N`
tokens (lowercase keys, integer values), and the paths of the notes or archived sources
the run touched, as code spans, at most ten followed by the number of the rest. `oplog.py`
SHALL refuse any other text and append nothing. `|` in a path SHALL be escaped.

#### Scenario: Large run
- **WHEN** a run touched 14 notes
- **THEN** the row lists 10 paths and "and 4 more"

#### Scenario: Free text passed
- **WHEN** a skill passes `--count summary=great`
- **THEN** `oplog.py` refuses with an error and appends nothing

### Requirement: Private terms never reach the log

`oplog.py` SHALL check every path against the "Always cut" terms of `content/_privacy.md`
and `content/_privacy.local.md`, read through `brain-export/scripts/privacy_sweep.py`,
and SHALL write a matching path segment as `[private]`. When that script is missing it
SHALL write the row unmasked and say so on stderr.

#### Scenario: Folder named after a client
- **WHEN** `_privacy.local.md` lists `Acme Labs` and a note lives in `CLIENTS/acme-labs/`
- **THEN** the row shows `CLIENTS/[private]/…` for that note

### Requirement: The log merges and stays out of indexes and exports

`.gitattributes` SHALL mark `content/_outputs/log.md` and `content/_outputs/metrics.md`
with `merge=union`. Indexes, lint and `/b:export --public` SHALL keep skipping the file
as they skip the rest of `content/_outputs/`. A reader of the log SHALL sort rows by time.

#### Scenario: Two clones appended rows
- **WHEN** two clones of a base each appended a row and one merges the other
- **THEN** git merges the file without a conflict and both rows are kept
