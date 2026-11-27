# Spec Delta

## Purpose

Defines how `/b:ingest` works through an inbox too large for one run: in batches of the
oldest sources, with the inbox as the checkpoint.

## ADDED Requirements

### Requirement: A backlog run takes N sources and stops

`/b:ingest --backlog [N]` SHALL take every YouTube URL given as an argument, then the
oldest sources from `content/_raw/inbox/` up to N in total (N is 10 when omitted), SHALL
run the normal ingest on them only, and SHALL end by reporting how many it ingested and
how many remain in the inbox, with the command for the next batch.

#### Scenario: 37 sources
- **WHEN** the inbox holds 37 sources and the owner runs `/b:ingest --backlog`
- **THEN** the plan covers the 10 oldest, and after writing the report says 27 remain

#### Scenario: Interrupted run
- **WHEN** a backlog run stops before writing
- **THEN** every inbox source is still in the inbox and the next run takes the same batch

### Requirement: Sources, attachments and order are defined by a script

`brain-ingest/scripts/inbox_order.py` SHALL list the inbox as JSON: the sources oldest
first, the attachments, the unusable files, and for each source whether its content
equals a file in `_raw/processed/`. Oldest SHALL mean a `YYYY-MM-DD` date in the file
name, else the frontmatter `date:`, else the modification time, ties broken by name.

#### Scenario: Dated file names
- **WHEN** the inbox holds `2026-03-02_call.md` and `2025-11-20_notes.md`
- **THEN** `2025-11-20_notes.md` comes first

### Requirement: Attachments and unusable files never count towards N

A source SHALL be a text file ingest reads. Image and media files SHALL be attachments:
they SHALL NOT count towards N and SHALL move with the source that references them. An
empty or unreadable file SHALL NOT count towards N and SHALL be named in every report.

#### Scenario: Empty oldest file
- **WHEN** the oldest file in the inbox is empty
- **THEN** it is named as unusable and the batch still takes N sources

#### Scenario: Screenshots next to a source
- **WHEN** the inbox holds a transcript and three `.png` files it references
- **THEN** the batch counts one source, and the images move to `ATTACHMENTS/` with it

### Requirement: Batch mode keeps its meaning

`--batch` alone SHALL take the whole inbox, as before. `--backlog` together with
`--batch` SHALL take N sources per run without the plan question. `--backlog` and a
number right after it SHALL be valid arguments; any other argument that is neither
`--batch` nor a YouTube URL SHALL still abort the call.

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

In an interactive backlog run the plan MAY propose to skip a source whose content equals
a file in `_raw/processed/`, and the owner MAY mark others to skip. On the owner's
confirmation ingest SHALL move each skipped file to `content/_raw/skipped/` and name it in
the report. Batch mode SHALL move nothing and SHALL report duplicates and unusable files.

#### Scenario: Duplicate of an archived source
- **WHEN** an inbox file has the same content as a file already in `_raw/processed/`
- **THEN** the plan proposes to skip it, and after the owner's OK it moves to `_raw/skipped/` and no note is written from it
