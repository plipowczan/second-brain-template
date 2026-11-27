# Spec Delta

## MODIFIED Requirements

### Requirement: One commit per update, or a backup without git

In a git instance, an upgrade SHALL end in exactly one commit. That commit SHALL contain
only the planned paths, the stamp, and `.kb-onboard.json` when it becomes tracked.
Unrelated uncommitted work SHALL stay uncommitted. In an instance without git,
brain-upgrade SHALL always create `.kb-upgrade-backup/<version>-<UTC timestamp>/` before
writing, SHALL copy every file it overwrites or deletes into it, SHALL write a
`backup.json` there that lists the versions and the files replaced, deleted and added,
each with the hash apply wrote, and SHALL name that folder in its report.

#### Scenario: Git instance with unrelated work in progress
- **WHEN** an upgrade is applied while an unrelated note has uncommitted edits
- **THEN** one new commit holds the upgrade, and the note's edits remain uncommitted

#### Scenario: Instance without git
- **WHEN** an upgrade is applied in a folder that is not a git repository
- **THEN** every replaced or deleted file has a copy in the backup folder, `backup.json` lists every added file, and the report names that folder

#### Scenario: Adoption without git that replaces nothing
- **WHEN** an adoption without git only adds files and the stamp
- **THEN** the backup folder exists, its `backup.json` lists the added files, and the folder the report names is that folder

## ADDED Requirements

### Requirement: An update without git can be undone from its backup

`upgrade.py undo --backup <folder>` SHALL restore every file the backup holds a copy of,
SHALL delete every file `backup.json` lists as added whose content still has the hash
apply wrote, SHALL keep and name every other listed file, and SHALL do this in one
transaction that puts everything back as it was if a write fails. It SHALL refuse a
folder without a valid `backup.json` and any path outside the instance, under `content/`,
or reached through a link or junction.

#### Scenario: Owner edited an added file
- **WHEN** a file the update added was edited after the update and the owner runs `undo`
- **THEN** that file is kept and named, and every other change of the update is undone

### Requirement: The engine leaves no temporary folders behind

The plan SHALL record the temporary folders the engine created for it. `commit` SHALL
delete them after a successful commit, and `apply` SHALL delete them in an instance
without git. A failed step SHALL leave its folders in place. No step SHALL delete folders
by pattern. The template's tests SHALL leave no `kb-upgrade-*` folder behind.

#### Scenario: Parallel upgrade in another base
- **WHEN** one base finishes its upgrade while another base's upgrade is waiting for review
- **THEN** the second upgrade's plan and payload folders still exist

### Requirement: Folders from fetch are deleted by name

`fetch` SHALL print the temporary folders it created. `upgrade.py cleanup --path
<folder>...` SHALL delete a folder only when it is a direct child of the system temp
directory and its name starts with `kb-upgrade-`, and SHALL refuse and name any other.

#### Scenario: Path outside the temp directory
- **WHEN** the skill passes a folder inside the base to `cleanup`
- **THEN** `cleanup` refuses, names the folder and deletes nothing

### Requirement: The commit message names a local source without its path

For a source that is a zip, a folder or a git clone, the commit body SHALL name the source
by its last path component and its commit. For a download it SHALL keep the URL.

#### Scenario: Release zip from the Downloads folder
- **WHEN** the owner upgrades with `--source C:\Users\<name>\Downloads\second-brain-template-0.5.0.zip`
- **THEN** the commit body says `Source: zip second-brain-template-0.5.0.zip` and the commit, without the folder

### Requirement: The plan warns when the base still ignores its render inputs

When the commit is going to track `.kb-onboard.json` and git reports the file as ignored,
the plan SHALL warn and name the ignore rule. brain-upgrade SHALL NOT edit `.gitignore`;
the skill SHALL offer to remove that rule after the upgrade commit, in a commit of its
own, on the owner's confirmation.

#### Scenario: Edited .gitignore with the old rule
- **WHEN** the owner's edited `.gitignore` still holds `.kb-onboard.json` and the file is untracked
- **THEN** the plan warns and names the line, the upgrade commit tracks the file, and `.gitignore` is unchanged until the owner agrees to the extra commit
