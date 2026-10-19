# Spec Delta

## Purpose

Makes every source path a note cites checkable: notes can cite several sources, ingest
records where the source file really ends up, and lint finds paths that lead nowhere and
proposes the fix.

## ADDED Requirements

### Requirement: Notes record sources in source or sources

A note's sources SHALL be recorded either in `source:` (one value) or in `sources:` (a
list of values). Every template skill and script that reads a note's sources SHALL accept
both forms, and a note SHALL NOT need to move from `source:` to `sources:`. A value is
one of these:

- a path under `_raw/`, relative to `content/`;
- a URL;
- a free-text description, such as the name of a conversation.

When a skill adds a second source to a note that has `source:`, it SHALL replace that
field with `sources:`, listing the earlier value first.

#### Scenario: Old note keeps passing
- **WHEN** the scanner runs on a note that has a single `source:` and no `sources:`
- **THEN** it reports no frontmatter or schema finding because of that field

#### Scenario: Second source
- **WHEN** ingest adds a source to a note whose frontmatter has `source: "_raw/processed/2026-05-01_a.md"`
- **THEN** the note's frontmatter has `sources:` listing `_raw/processed/2026-05-01_a.md` first and the new archive path second, and no `source:` field

### Requirement: Ingest records the final archive path

After a run, every `_raw/` path that brain-ingest wrote into a note's source fields SHALL
point to where that file is after the run, under `_raw/processed/`, for file sources and
YouTube sources alike. brain-ingest's final checklist SHALL check that each such path
exists. It SHALL report any path that does not exist before it reports the run as
complete.

#### Scenario: File source
- **WHEN** `content/_raw/inbox/report.md` is ingested on 2026-10-20
- **THEN** every note that cites it lists `_raw/processed/2026-10-20_report.md`, and that file exists

#### Scenario: Name already taken
- **WHEN** `_raw/processed/2026-10-20_report.md` already exists at the time of the move
- **THEN** ingest archives the file under a unique name and writes that name into the notes

### Requirement: Lint reports source paths that do not exist

The lint scanner SHALL report every scanned note whose source fields hold a `_raw/` path
that does not exist under `content/`. A value written with a leading `content/` SHALL be
resolved the same way. The scanner SHALL skip URLs, wikilinks and every other value that
is not a `_raw/` path.

#### Scenario: Missing inbox path
- **WHEN** a note has `source: "_raw/inbox/talk.md"` and no such file exists
- **THEN** the scanner reports the note and the missing path

#### Scenario: URL and description
- **WHEN** a note has `sources:` listing `https://example.com/post` and `Call with the vendor`
- **THEN** the scanner does not report the note

### Requirement: Lint proposes the fix for a moved inbox file

For a missing `_raw/inbox/<name>` path, the scanner SHALL look for files in
`_raw/processed/` whose names end in `_<name>`. When exactly one exists, the report SHALL
give its path as the replacement. When several exist, it SHALL list them all and propose
none. When none exists, it SHALL report the missing path without a fix.

#### Scenario: One archived copy
- **WHEN** a note cites the missing `_raw/inbox/talk.md` and `_raw/processed/2026-07-02_talk.md` exists
- **THEN** the report proposes replacing the path with `_raw/processed/2026-07-02_talk.md`

#### Scenario: Two archived copies
- **WHEN** both `_raw/processed/2026-07-02_talk.md` and `_raw/processed/2026-08-10_talk.md` exist
- **THEN** the report lists both paths and proposes no replacement

### Requirement: Missing source paths are a warning in this version

A missing source path SHALL be a warning: it SHALL NOT block the pre-commit hook, and the
lint report SHALL list it among the warnings, not among the errors.

#### Scenario: Pre-commit with only missing sources
- **WHEN** the optional pre-commit hook runs on a base whose only findings are missing source paths
- **THEN** the commit proceeds
