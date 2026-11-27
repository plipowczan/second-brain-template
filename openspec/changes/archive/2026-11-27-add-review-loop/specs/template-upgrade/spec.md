# Spec Delta

## MODIFIED Requirements

### Requirement: One commit per update, or a backup without git

In a git instance, an upgrade SHALL end in exactly one commit. That commit SHALL contain
only the planned paths, the stamp, and `.kb-onboard.json` when it becomes tracked.
Unrelated uncommitted work SHALL stay uncommitted. In an instance without git,
brain-upgrade SHALL always create `.kb-upgrade-backup/<version>-<UTC timestamp>/` before
writing, SHALL copy every file it overwrites or deletes into it, SHALL write a
`backup.json` there that lists the versions and, for every path apply writes or deletes,
its hash before and after, and SHALL name that folder in its report.

#### Scenario: Git instance with unrelated work in progress
- **WHEN** an upgrade is applied while an unrelated note has uncommitted edits
- **THEN** one new commit holds the upgrade, and the note's edits remain uncommitted

#### Scenario: Instance without git
- **WHEN** an upgrade is applied in a folder that is not a git repository
- **THEN** every replaced or deleted file has a copy in the backup folder, `backup.json` lists every path apply wrote or deleted, added files included, and the report names that folder

#### Scenario: Adoption without git that replaces nothing
- **WHEN** an adoption without git only adds files and the stamp
- **THEN** the backup folder exists, its `backup.json` lists the added files and the stamp, and the folder the report names is that folder

## ADDED Requirements

### Requirement: An update without git can be undone from its backup

`upgrade.py undo --backup <folder>` SHALL refuse unless the current stamp equals the stamp
`backup.json` recorded after apply. It SHALL restore a listed path only while that path
still has the hash apply left, by putting back its copy or deleting a file apply added,
and SHALL keep and name every listed path changed since. It SHALL do this in one
transaction that puts everything back if a write fails.

#### Scenario: Owner edited an added file
- **WHEN** a file the update added was edited after the update and the owner runs `undo`
- **THEN** that file is kept and named, and every other change of the update is undone

#### Scenario: Older backup first
- **WHEN** two updates ran without git and the owner runs `undo` on the older backup
- **THEN** `undo` refuses and names the newer backup

### Requirement: Undo writes only what apply wrote

`undo` SHALL write only paths `backup.json` lists, SHALL refuse a folder without a valid
`backup.json`, and SHALL refuse any path outside the instance, under `content/` other
than `content/WRITING_STYLE.md`, or reached through a link or junction.

#### Scenario: Re-rendered writing style
- **WHEN** the update re-rendered `content/WRITING_STYLE.md` on request
- **THEN** `undo` puts back the previous file

### Requirement: The engine cleans up the folders of its plan

`commit`, as its last step, SHALL delete the temporary folder that holds the plan and its
payload, after the commit in a git instance and after reporting the backup in one without
git, and SHALL keep the download folder. `apply` SHALL delete nothing, and a failed step
SHALL delete nothing. No step SHALL delete folders by pattern. The template's tests SHALL
leave no `kb-upgrade-*` folder in the system temp directory.

#### Scenario: Parallel upgrade in another base
- **WHEN** one base commits its upgrade while another base's upgrade is waiting for review
- **THEN** the second upgrade's plan and payload folders still exist

#### Scenario: Merge before commit
- **WHEN** apply leaves a file waiting for a merge
- **THEN** the plan's payload still exists when the owner merges, and is deleted only by `commit`

#### Scenario: Offline upgrade after an adoption
- **WHEN** the adoption is committed and the owner, now offline, plans the upgrade with the archive the adoption's `plan` downloaded
- **THEN** that archive still exists

### Requirement: A folder is deleted only after the same checks

Every deletion of a temporary folder, by `commit` or by `upgrade.py cleanup --path
<folder>...`, SHALL require that the folder is a direct child of the system temp
directory, that its name starts with `kb-upgrade-`, and that no link or junction is on
its path, and SHALL refuse and name any other. `plan` and `fetch` SHALL print the folders
they created.

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
