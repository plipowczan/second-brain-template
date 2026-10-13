# Spec Delta

## Purpose

Brings instances created before stamps existed under the update mechanism. That includes
generations older than the first tagged release. Adoption aligns the instance with the
nearest template release in its own reviewed commit, before any upgrade.

## ADDED Requirements

### Requirement: Adoption is explicit and separate from upgrading

brain-upgrade SHALL stop a plain upgrade in an instance that has no `.kb-template.json`,
and SHALL suggest `--adopt`. It SHALL refuse `--adopt` in an instance that already has a
stamp. Adoption SHALL NOT go past the nearest release. An upgrade to a newer version
SHALL be a separate run with its own plan and its own commit.

#### Scenario: Plain upgrade without a stamp
- **WHEN** `/b:upgrade` runs in an instance that has no `.kb-template.json`
- **THEN** nothing changes and the owner is told to adopt first with `--adopt`

#### Scenario: Adopt with a stamp present
- **WHEN** `--adopt` runs in an instance that has a stamp
- **THEN** brain-upgrade refuses and points to a plain upgrade

### Requirement: Unmodified older template files are recognised from history

During adoption, a local file SHALL count as unmodified if its content hash appears in the
release's history index for the same path. Every other file that differs from the nearest
release SHALL count as a local edit.

#### Scenario: File from an older template state
- **WHEN** an instance's `.claude/hooks/load_vault_map.py` matches content the template shipped before `v0.1.0`
- **THEN** it counts as unmodified

#### Scenario: Content the template never shipped
- **WHEN** an owned file's content matches no state in the index
- **THEN** it counts as a local edit

### Requirement: The nearest release is identified

Adoption SHALL determine the nearest release R: the tagged release, no newer than the
source version, whose files the instance matches best, with ties going to the older
release. R SHALL always be a tagged release. The adoption dry run SHALL report R and show
R's `CHANGELOG.md` section.

#### Scenario: Generation older than the first release
- **WHEN** an instance from before `v0.1.0` that still has the pre-rename `.claude/skills/ingest/` directory is adopted
- **THEN** R is reported as `0.1.0`

#### Scenario: Instance created between two releases
- **WHEN** an instance's files match the template's `0.2.0` release better than `0.1.0`, and the source is `0.2.0`
- **THEN** R is `0.2.0`, and after the adoption a plain upgrade reports the instance as up to date

### Requirement: Adoption aligns files with the nearest release, forward only

Adoption SHALL plan these actions:

- update each unmodified file from a template state older than R to R's content;
- add each owned file that R ships and the instance lacks, as an addition the owner can
  deselect;
- delete each unmodified file at a path R does not ship, as a selected deletion.

Adoption SHALL leave unchanged both unmodified files from a state newer than R and locally
edited files. No file SHALL ever be moved to an older template state. Seeded files and
author files the template never shipped SHALL be left alone.

#### Scenario: Oldest generation brought to 0.1.0
- **WHEN** an instance without `CHANGELOG.md`, `ENVIRONMENTS.md`, `LICENSE`, `.github/` and `.claude/agents/` is adopted with R = `0.1.0`
- **THEN** the plan adds those files and updates its unmodified older files to their `0.1.0` content

#### Scenario: File re-pulled from a newer state is not rewound
- **WHEN** one unmodified file matches a template state newer than R
- **THEN** the file is left as it is, and the stamp records its own hash as its baseline

#### Scenario: Locally edited file
- **WHEN** an owned file was edited by the owner
- **THEN** adoption leaves it unchanged, reports it, and the stamp records R's hash as its baseline, so the next upgrade still treats it as edited

### Requirement: The nearest release's content is obtained like any source

Adoption SHALL take R's files from one of these:

- the source itself, when the source is R's release (its tag or its archive), not just a
  tree that carries R's version number;
- the tag `v<R>` of a git-clone source;
- a download of R's release archive from the repository;
- an archive or directory the owner passes with `--base`.

Without network and without `--base`, adoption SHALL stop before any change and name the
release it needs.

#### Scenario: Git clone source holds the older release
- **WHEN** the source is a git clone of the template checked out at a commit other than the tag `v<R>`
- **THEN** R's files are read from the clone's tag `v<R>`, without network access

#### Scenario: Offline without the older release
- **WHEN** R is older than the source version, there is no network, the source is a release `.zip`, and no `--base` is given
- **THEN** nothing changes and the owner is told which release archive to pass with `--base`

### Requirement: Rendered files are not written during adoption

Adoption SHALL NOT write `CLAUDE.md`, `AGENTS.md` or `content/WRITING_STYLE.md`. For each
of them it SHALL compare the local file with a rendering of R's template from
`.kb-onboard.json`. When they are equal, the stamp SHALL record the file's output hash.
Otherwise, or when `.kb-onboard.json` is missing, the stamp SHALL record `null`. The
difference to a rendering of the new source SHALL be shown as a proposal.

#### Scenario: Untouched rendered file
- **WHEN** an adopted instance's `AGENTS.md` equals the rendering of R's `AGENTS.template.md`
- **THEN** the stamp records its output hash, and a later upgrade may re-render it on request

#### Scenario: Hand-edited rendered file
- **WHEN** an adopted instance's `AGENTS.md` differs from that rendering
- **THEN** `AGENTS.md` is unchanged, the stamp records `null` for its output hash, and later upgrades only propose changes to it

### Requirement: Adoption lands as its own commit after review

Adoption SHALL follow the same review and apply rules as an upgrade. The stamp SHALL name
R and SHALL be written only when the adoption plan is applied. In a git instance the
adoption SHALL be exactly one commit, separate from any upgrade commit.

#### Scenario: Owner rejects the adoption plan
- **WHEN** the owner rejects the adoption plan
- **THEN** no stamp is written and no file changes

#### Scenario: Adoption followed by an upgrade
- **WHEN** a git instance is adopted with R = `0.1.0` and then upgraded to `0.2.0`
- **THEN** there are two new commits: the adoption, whose stamp names `0.1.0`, and the upgrade, whose stamp names `0.2.0`
