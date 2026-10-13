# Spec Delta

## Purpose

Brings instances created before stamps existed under the update mechanism. That includes
generations older than the first tagged release, and none of them needs git or network
access.

## ADDED Requirements

### Requirement: Adoption is explicit

brain-upgrade SHALL stop a plain upgrade in an instance that has no `.kb-template.json`,
and SHALL suggest `--adopt`. It SHALL refuse `--adopt` in an instance that already has a
stamp.

#### Scenario: Plain upgrade without a stamp
- **WHEN** `/b:upgrade` runs in an instance that has no `.kb-template.json`
- **THEN** nothing changes and the owner is told to run it with `--adopt`

#### Scenario: Adopt with a stamp present
- **WHEN** `--adopt` runs in an instance that has a stamp
- **THEN** brain-upgrade refuses and points to a plain upgrade

### Requirement: Unmodified older template files are recognised from history

During adoption, a local file SHALL count as unmodified if its content hash appears in the
release's history index for the same path, or equals the new source. Unmodified files
SHALL then follow the same three-way rules as a stamped upgrade, with the local hash as
the baseline. Every other differing file SHALL count as a local edit.

#### Scenario: File from an older template state
- **WHEN** an instance's `.claude/hooks/load_vault_map.py` matches the content the template shipped at `v0.1.0`
- **THEN** it is updated to the new version without a question

#### Scenario: File re-pulled by hand from a later state
- **WHEN** one file matches a template state newer than the rest of the instance
- **THEN** it also counts as unmodified

#### Scenario: Content the template never shipped
- **WHEN** an owned file's content matches no state in the index and differs from the new source
- **THEN** it is a conflict, and the owner chooses keep, overwrite or merge

### Requirement: The starting version is identified

Adoption SHALL report the release whose files the instance matches best, with ties going
to the older release. A best match older than the first tagged release SHALL be reported
as `0.0.0`. That version SHALL decide which `CHANGELOG.md` entries the dry run shows.

#### Scenario: Pre-release generation
- **WHEN** an instance from before `v0.1.0` is adopted
- **THEN** its starting version is reported as `0.0.0`, and every `CHANGELOG.md` entry up to the source version is shown

### Requirement: Older generations get the files they lack and lose the ones the template dropped

Adoption SHALL plan owned files that the instance lacks as additions, each of which the
owner can deselect. It SHALL plan unmodified files at paths the source no longer ships as
selected deletions.

#### Scenario: Oldest generation
- **WHEN** an instance without `CHANGELOG.md`, `ENVIRONMENTS.md` and `.claude/agents/` and with the pre-rename `.claude/skills/ingest/` directory is adopted
- **THEN** the plan adds the missing files, adds `.claude/skills/brain-ingest/`, and proposes deleting the unmodified `.claude/skills/ingest/` files

### Requirement: Rendered files are not rewritten during adoption

Adoption SHALL NOT write `CLAUDE.md`, `AGENTS.md` or `content/WRITING_STYLE.md`. It SHALL
show the difference between each file and a fresh rendering from the source as a proposal.

#### Scenario: Rendered instructions of an old generation
- **WHEN** an instance with its original `AGENTS.md` is adopted
- **THEN** `AGENTS.md` is unchanged and the plan shows the difference to the new rendering

### Requirement: Adoption and upgrade land together after review

Adoption SHALL produce one plan covering the adoption and the upgrade to the source
version, under the same review and apply rules as a stamped upgrade. The stamp SHALL be
written only when that plan is applied, and in a git instance the result SHALL be a
single commit.

#### Scenario: Owner rejects the plan
- **WHEN** the owner rejects the adoption plan
- **THEN** no stamp is written and no file changes

#### Scenario: Owner approves the plan
- **WHEN** the owner approves the adoption plan in a git instance
- **THEN** one commit holds the planned file changes and a stamp naming the source version
