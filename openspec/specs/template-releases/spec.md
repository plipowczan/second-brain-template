# template-releases Specification

## Purpose
Defines how a template version is numbered, released and tied to a commit, so that every
instance can name the version it runs and fetch any released version.

## Requirements

### Requirement: One version number, kept in the manifest

The template version SHALL follow SemVer and SHALL be stored only in the `version` field
of `.kb-manifest.json`. `package.json` SHALL NOT carry a `version` field.

#### Scenario: Version agrees with the changelog
- **WHEN** the release check runs
- **THEN** it passes only if the manifest version equals the newest released heading `## [X.Y.Z]` in `CHANGELOG.md`

#### Scenario: Second version field
- **WHEN** `package.json` contains a `version` field
- **THEN** the release check fails and names the field

### Requirement: A release is one tagged commit

A release SHALL be a single commit on `main` that:

- renames `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`;
- sets the manifest version to `X.Y.Z`;
- regenerates the history index.

It SHALL be tagged with an annotated tag `vX.Y.Z` and published as a GitHub Release whose
notes are that `CHANGELOG.md` section. A published tag SHALL NOT be moved or reused.

#### Scenario: The tag names the release commit
- **WHEN** `vX.Y.Z` is resolved to a commit
- **THEN** that commit's manifest version is `X.Y.Z` and its `CHANGELOG.md` has `## [X.Y.Z]` as the newest released section

#### Scenario: Defect found after a release
- **WHEN** a released version turns out to be broken
- **THEN** the fix ships as a new patch release, and the existing tag keeps pointing at its original commit

### Requirement: Each release ships the template's history index

Each release SHALL contain an index of the content hash of every owned-class and
author-class file at every template state reachable from the release commit. The index
SHALL include states older than the first tagged release, and SHALL record for each hash
which states shipped it and which release those states belong to.

#### Scenario: A renamed skill is still recognised
- **WHEN** the `0.2.0` index is generated
- **THEN** it contains the hashes that `.claude/skills/ingest/SKILL.md` had before the skills were renamed to `brain-*`

### Requirement: The changelog has one section per type in each version

Within one version block of `CHANGELOG.md`, including `[Unreleased]`, a Keep a Changelog
section heading (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`) SHALL
appear at most once.

#### Scenario: Duplicated section heading
- **WHEN** `[Unreleased]` contains `### Fixed` twice and the release check runs
- **THEN** the check fails and names the version block and the heading
