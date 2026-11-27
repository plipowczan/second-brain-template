# Spec Delta

## Purpose

Defines how `/b:ingest` works through an inbox too large for one run: in batches of the
oldest sources, with the inbox as the checkpoint.

## ADDED Requirements

### Requirement: A backlog run takes the N oldest sources and stops

`/b:ingest --backlog [N]` SHALL take the N oldest sources from `content/_raw/inbox/` (N is
10 when omitted), counting YouTube URLs given as arguments towards N, SHALL run the
normal ingest on them only, and SHALL end by reporting how many it ingested and how many
remain in the inbox, with the command for the next batch. Oldest SHALL mean: a
`YYYY-MM-DD` date in the file name, else the frontmatter `date:`, else the file's
modification time, ties broken by name.

#### Scenario: 37 sources
- **WHEN** the inbox holds 37 sources and the owner runs `/b:ingest --backlog`
- **THEN** the plan covers the 10 oldest, and after writing the report says 27 remain

#### Scenario: Interrupted run
- **WHEN** a backlog run stops before writing
- **THEN** every source is still in the inbox and the next run takes the same batch

### Requirement: Batch mode keeps its meaning

`--batch` alone SHALL take the whole inbox, as before. `--backlog` together with
`--batch` SHALL take N sources per run without the plan question.

#### Scenario: Script with --batch
- **WHEN** a script runs `/b:ingest --batch` on an inbox of 37 sources
- **THEN** all 37 are ingested in that run

### Requirement: A large interactive inbox is taken in batches

Without `--backlog` and `--batch`, when the inbox holds more than 10 sources, ingest SHALL
behave as `--backlog 10` and SHALL say so in its plan message. It SHALL still ask at most
once per run.

#### Scenario: 12 sources, no flag
- **WHEN** the owner runs `/b:ingest` with 12 sources in the inbox
- **THEN** the plan covers the 10 oldest and says that 2 wait for the next run

### Requirement: A skipped source does not come back

In a backlog run the plan MAY propose to skip a source that is empty, unreadable, or has
the same content as a file in `_raw/processed/`. On the owner's confirmation ingest SHALL
move it to `content/_raw/skipped/` and name it in the report. Batch mode SHALL skip
nothing.

#### Scenario: Duplicate of an archived source
- **WHEN** an inbox file has the same content as a file already in `_raw/processed/`
- **THEN** the plan proposes to skip it, and after the owner's OK it moves to `_raw/skipped/` and no note is written from it
