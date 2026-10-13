# Spec Delta

## Purpose

Records in each instance which template version it runs and what the template shipped.
With that record, an update can tell template files from local edits without network
access.

## ADDED Requirements

### Requirement: The stamp records version, commit and shipped hashes

An instance SHALL carry `.kb-template.json` at its root, readable with the Python standard
library alone. It SHALL contain:

- the stamp format number and the template repository;
- the template version;
- the template commit as a 40-character SHA, or `null`;
- the UTC time of the last write;
- a map from each template-owned file path to its content hash;
- for each rendered file, its template source path, the hash of that template source, and
  the hash of the output as written, or `null` when an adoption could not prove the file
  untouched.

#### Scenario: Stamp after a completed upgrade
- **WHEN** an upgrade to version `X.Y.Z` completes
- **THEN** `.kb-template.json` holds version `X.Y.Z`, the repository, the commit or `null`, the time, the owned-file hashes and the rendered-file entries

### Requirement: Hashes ignore line endings

A content hash SHALL be computed so that a text file differing from the shipped content
only in CRLF versus LF line endings produces the same hash. Binary files SHALL be hashed
byte for byte.

#### Scenario: File checked out with CRLF on Windows
- **WHEN** an owned file in the instance has CRLF line endings and is otherwise identical to what the template shipped
- **THEN** brain-upgrade treats it as unmodified

### Requirement: Hashes record what the template shipped, not local content

For each owned file, the stamp SHALL record the hash of the file as shipped by the
template version it names. It SHALL do so even when the owner kept a local version of
that file.

#### Scenario: A kept local edit stays visible
- **WHEN** the owner keeps a locally edited `schema.yml` during an upgrade
- **THEN** the stamp records the new template's hash for `schema.yml`, and the next upgrade still reports the file as locally edited

### Requirement: The commit is recorded only when the source proves it

The stamp SHALL record the commit of the git ref used, or the commit stored in a release
archive's zip comment. It SHALL record `null` when the source cannot prove a commit.

#### Scenario: Unpacked download
- **WHEN** the update source is an unpacked directory without git metadata
- **THEN** the stamp records the version and `commit: null`

#### Scenario: Release archive
- **WHEN** the update source is a release `.zip` whose comment holds a commit SHA
- **THEN** the stamp records that SHA

### Requirement: Onboarding writes the stamp

`/b:onboard` SHALL write `.kb-template.json` after the rendered files are written. The
stamp SHALL record:

- the manifest version;
- the hashes of every owned file present;
- the template and output hashes of the three rendered files;
- the commit, only when HEAD is the commit tagged `v<version>`, and `null` otherwise.

#### Scenario: Onboarding a release clone
- **WHEN** `/b:onboard` finishes in a clone checked out at the tag `v0.2.0`
- **THEN** the stamp holds version `0.2.0`, the tagged commit, and hashes for the owned and rendered files

#### Scenario: Onboarding a "Use this template" copy
- **WHEN** `/b:onboard` finishes in a repository created with "Use this template"
- **THEN** the stamp holds the manifest version and `commit: null`

### Requirement: Stamp and render inputs are versioned with the instance

The template SHALL NOT git-ignore `.kb-template.json` or `.kb-onboard.json`. When an
upgrade finds `.kb-onboard.json` present but untracked, the upgrade commit SHALL add it,
and the dry run SHALL say so.

#### Scenario: Instance cloned to another machine
- **WHEN** an upgraded instance is cloned elsewhere
- **THEN** the clone contains both `.kb-template.json` and `.kb-onboard.json`
