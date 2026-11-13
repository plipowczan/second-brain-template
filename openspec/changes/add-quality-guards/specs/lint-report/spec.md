# Spec Delta

## Purpose

Makes the lint report useful and honest: it is not run on a base too small to judge,
every finding leads to a next step, the report says what to fix first, and a clean
result is not presented as proof that the content is right.

## ADDED Requirements

### Requirement: Lint stops on a base that is too small

When the lint scanner counts fewer than 10 notes, brain-lint SHALL say that it is too
early for a lint, give the count, and stop without saving a report. The scanner itself
SHALL keep reporting at any size.

#### Scenario: Four notes
- **WHEN** the user runs `/b:lint` on a base with four notes
- **THEN** brain-lint says it is too early, reports the count of four, and writes nothing under `content/_outputs/reports/`

### Requirement: Every finding names a note and a next step

In the saved report, every finding SHALL name the note it concerns and the next step:
the edit to make or the skill to run.

#### Scenario: Missing summary
- **WHEN** a note lacks `summary:`
- **THEN** the report names that note and tells the reader to add a one-line `summary:`

#### Scenario: Missing source with a fix
- **WHEN** the scanner proposes a replacement for a missing source path
- **THEN** the report names the note, the missing path and the replacement to write

### Requirement: The report ends with a fix-first list

The saved report SHALL end with an ordered list of what to fix first. The order SHALL
follow what a fix unblocks:

1. findings that hide a note from other checks, such as missing frontmatter or an unknown
   type;
2. single fixes that clear many findings, such as one renamed tag or one moved file;
3. findings that concern one note.

#### Scenario: Mixed findings
- **WHEN** a report has one note without frontmatter, one tag typo used in twelve notes, and three stubs
- **THEN** the fix-first list starts with the note without frontmatter, follows with the tag typo, and puts the stubs last

### Requirement: A clean report says what clean means

When a report has no findings, it SHALL say that this means the base is in order, not
that its content is true, and SHALL point to `LIMITS.md`.

#### Scenario: Nothing found
- **WHEN** the scanners report no findings on a base with fifty notes
- **THEN** the report states that a clean lint covers structure, not truth, and refers to `LIMITS.md`

### Requirement: Warning classes never block

The lint scanner SHALL name its warning classes in its output, and they SHALL include
missing source paths and contradiction markers. Warning findings SHALL appear in the
report under warnings, SHALL NOT block the optional pre-commit hook, and SHALL be listed
apart from other issues in the scheduled maintenance summary. The scanner SHALL keep every
existing class name and output field unchanged.

#### Scenario: Existing consumer
- **WHEN** a script reads `issues["missing_frontmatter"]` and `counts` from the scanner's output after this change
- **THEN** it gets the same values it got before for the same notes

#### Scenario: Maintenance summary
- **WHEN** the scheduled maintenance workflow runs on a base with three missing source paths
- **THEN** its summary lists them under warnings, not under issues

### Requirement: Notes valid before this change stay valid

A note that produced no finding outside the new warning classes under the previous
scanner SHALL produce none under the new one, including notes that use `source:` and
notes without the new sections.

#### Scenario: Note from version 0.2.1
- **WHEN** the scanner runs on a note that had no findings under version `0.2.1` and cites an existing file in `source:`
- **THEN** the scanner reports no finding for it
