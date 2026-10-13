# template-upgrade Specification

## Purpose
Lets the owner of an instance pull a newer template version into it. The owner reviews
the plan first, the update lands as one change, and the owner's notes are never touched.

## Requirements

### Requirement: The update source works without git and offline

brain-upgrade SHALL accept as its source:

- a local directory (a template clone or an unpacked release);
- a local release `.zip`;
- when neither is given, a release archive downloaded over HTTPS from the repository
  recorded in the stamp. `--to <version>` selects the version, and the latest GitHub
  Release is the default.

Downloading SHALL NOT require git. Once the source is local, planning SHALL NOT require
network access.

#### Scenario: Offline with a release archive
- **WHEN** there is no network and `--source` points to a release `.zip`
- **THEN** the dry run completes

#### Scenario: Offline without a source
- **WHEN** there is no network and no `--source` is given
- **THEN** brain-upgrade stops before changing anything and explains how to pass a release `.zip` or a local clone

#### Scenario: Git clone as the source
- **WHEN** `--source` is a git working copy
- **THEN** files are read from the requested ref (by default the tag `v<manifest version>`, else HEAD with a "not a release" warning), and untracked or ignored files in that working copy are never used

#### Scenario: Downloaded archive is kept
- **WHEN** brain-upgrade downloads a release archive
- **THEN** it prints the archive's local path so that the same file can be passed as `--source` later, offline

### Requirement: The upgrade logic runs from the source version

The upgrade logic SHALL be executed from the source being installed, not from the copy in
the instance. It SHALL be runnable against an instance path from an unpacked release.

#### Scenario: Instance that has no brain-upgrade yet
- **WHEN** the engine of an unpacked `0.2.0` release is run with `--instance` pointing to a base created before `0.2.0`
- **THEN** it plans the adoption (or, for a stamped base, the update) exactly as an instance-side run would

### Requirement: Dry run by default

brain-upgrade SHALL NOT change any file in the instance until the owner approves a plan.
The dry run SHALL show:

- the source and its location;
- the version range;
- every `CHANGELOG.md` entry between the two versions, with **BREAKING** entries marked;
- a per-file plan, with a diff for any file on request.

#### Scenario: Plain run
- **WHEN** the owner runs `/b:upgrade` and has not yet approved a plan
- **THEN** every file in the instance is byte-identical before and after, and the plan and changelog entries are shown

### Requirement: Owned files follow a three-way decision

For each template-owned file, brain-upgrade SHALL compare three hashes: the stamp baseline
(B), the new source (S) and the local file (L).

#### Scenario: Pristine file changed upstream
- **WHEN** L equals B and S differs from B
- **THEN** the file is updated to S without a question

#### Scenario: Local edit, upstream unchanged
- **WHEN** S equals B and L differs from B
- **THEN** the local file is kept and reported as locally edited, without a question

#### Scenario: Both sides changed
- **WHEN** B, S and L all differ
- **THEN** the owner chooses keep, overwrite or merge for that file, and nothing is written for it before that choice

#### Scenario: New template file
- **WHEN** S ships a file that has no baseline and does not exist locally
- **THEN** the file is added

#### Scenario: New template file collides with an instance file
- **WHEN** S ships a file that has no baseline, but a different local file exists at that path
- **THEN** it is treated as a conflict and the owner chooses

#### Scenario: Owner deleted a template file
- **WHEN** B and S exist but the local file is absent
- **THEN** the file stays absent unless the owner chooses to restore it

### Requirement: Files removed from the template are proposed for deletion

When a path has a baseline but the new source no longer ships it, the dry run SHALL
propose deleting the local file. The proposal SHALL be selected when L equals B. It SHALL
be unselected, with a warning, when the file was edited locally. A file SHALL be deleted
only if the proposal is still selected when the owner approves the plan.

#### Scenario: Renamed skill directory
- **WHEN** the new version renames a skill directory and the instance's old copy is pristine
- **THEN** the plan adds the new directory and proposes deleting the old one, selected

#### Scenario: Edited file the template removed
- **WHEN** the template removed a file the owner had edited
- **THEN** the deletion is proposed unselected with a warning, and the file stays unless the owner selects it

### Requirement: Rendered files are re-rendered only on request and only if untouched

brain-upgrade SHALL re-render `CLAUDE.md`, `AGENTS.md` and `content/WRITING_STYLE.md` only
when the owner asks for it. It SHALL use the source's templates and `.kb-onboard.json`,
and SHALL write the result only if the local file still matches the output hash in the
stamp. A `null` output hash never matches. In every other case it SHALL show the
difference as a proposal and leave the file unchanged.

#### Scenario: Untouched file, re-render requested
- **WHEN** the owner requests a re-render and `AGENTS.md` matches its recorded output hash
- **THEN** `AGENTS.md` is rewritten from the new template and the stamp records the new hashes

#### Scenario: Hand-edited file
- **WHEN** `AGENTS.md` differs from its recorded output hash
- **THEN** the file is not written, and the difference to a fresh rendering is shown as a proposal

#### Scenario: New placeholder without a value
- **WHEN** the new template uses a placeholder that `.kb-onboard.json` has no value for
- **THEN** the owner is asked for the value, it is saved to `.kb-onboard.json`, and the render proceeds

#### Scenario: Render inputs missing
- **WHEN** `.kb-onboard.json` does not exist
- **THEN** rendered files are only reported as proposals

### Requirement: Notes are never touched

An upgrade SHALL NOT create, change or delete any file under `content/`. The single
exception is `content/WRITING_STYLE.md`, and only when its re-render was explicitly
requested.

#### Scenario: Completed upgrade
- **WHEN** an upgrade completes without a requested re-render
- **THEN** no file under `content/` was created, changed or deleted

### Requirement: Only the reviewed plan is applied

brain-upgrade SHALL check every planned path against the plan before the first write. It
SHALL stop without writing anything if any of them changed after the dry run. In a git
instance it SHALL refuse to apply while a planned path has uncommitted changes.

#### Scenario: File edited after the dry run
- **WHEN** a planned file is edited between the dry run and apply
- **THEN** apply stops before its first write and asks for a new dry run

#### Scenario: Uncommitted work on a planned file
- **WHEN** a git instance has uncommitted changes in a file the plan would write
- **THEN** apply refuses until those changes are committed or stashed

### Requirement: One commit per update, or a backup without git

In a git instance, an upgrade SHALL end in exactly one commit. That commit SHALL contain
only the planned paths, the stamp, and `.kb-onboard.json` when it becomes tracked.
Unrelated uncommitted work SHALL stay uncommitted. In an instance without git,
brain-upgrade SHALL copy every file it overwrites or deletes to
`.kb-upgrade-backup/<version>-<UTC timestamp>/` before writing, and SHALL name that
folder in its report.

#### Scenario: Git instance with unrelated work in progress
- **WHEN** an upgrade is applied while an unrelated note has uncommitted edits
- **THEN** one new commit holds the upgrade, and the note's edits remain uncommitted

#### Scenario: Instance without git
- **WHEN** an upgrade is applied in a folder that is not a git repository
- **THEN** every replaced or deleted file has a copy in the backup folder, and the report names that folder

### Requirement: Up-to-date instances and downgrades

brain-upgrade SHALL report "up to date" and change nothing when the source version equals
the stamp version and no owned file needs action. It SHALL refuse a source version older
than the stamp version.

#### Scenario: Already current
- **WHEN** the stamp and the source both say `0.2.0` and every owned file matches
- **THEN** brain-upgrade reports that the instance is up to date and writes nothing

#### Scenario: Older source
- **WHEN** the stamp says `0.2.1` and the source is `0.2.0`
- **THEN** brain-upgrade refuses and changes nothing
