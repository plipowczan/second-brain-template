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
network access. A local source SHALL need the owner's consent.

#### Scenario: Offline with a release archive
- **WHEN** there is no network, `--source` points to a release `.zip`, and the owner accepted it
- **THEN** the dry run completes

#### Scenario: Offline without a source
- **WHEN** there is no network and no `--source` is given
- **THEN** brain-upgrade stops before changing anything and explains how to pass a release `.zip` or a local clone

#### Scenario: Git clone as the source
- **WHEN** `--source` is a git working copy
- **THEN** files are read from the requested ref (by default the tag `v<manifest version>`, else HEAD with a "not a release" warning), and untracked or ignored files in that working copy are never used

#### Scenario: Downloaded archive is kept
- **WHEN** brain-upgrade downloads a release archive
- **THEN** it prints the archive's local path, so that the same file can be passed as `--source` later, offline, with the owner's consent

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

### Requirement: Rendered files are re-rendered on request, or when the template of AGENTS.md changed, and only if untouched

brain-upgrade SHALL re-render `CLAUDE.md`, `AGENTS.md` and `content/WRITING_STYLE.md` when
the owner asks for it. It SHALL also re-render `AGENTS.md`, and no other file, unless the
owner declines, when the source's template for it differs from the template hash the stamp
records for it, whether or not the update range holds a **BREAKING** entry. It SHALL
render from the source's templates and `.kb-onboard.json`, and SHALL write the result only
if the local file matches the stamp's output hash, which a `null` hash never does.
Otherwise it SHALL show a proposal and leave the file unchanged, and the summary SHALL say
whether the file was edited or cannot be proven untouched because its output hash is
`null`.

#### Scenario: Untouched file, re-render requested
- **WHEN** the owner requests a re-render and `AGENTS.md` matches its recorded output hash
- **THEN** `AGENTS.md` is rewritten from the new template and the stamp records the new hashes

#### Scenario: Breaking release, untouched file
- **WHEN** the update range holds a **BREAKING** entry, the source's `AGENTS.template.md` differs from the stamp's template hash for `AGENTS.md`, no re-render was requested, and `AGENTS.md` matches its recorded output hash
- **THEN** the plan says `AGENTS.md` will be re-rendered and why, and without a refusal it is rewritten, while `content/WRITING_STYLE.md` and `CLAUDE.md` stay unchanged

#### Scenario: No breaking entry
- **WHEN** the update range holds no **BREAKING** entry, the template for `AGENTS.md` changed, no re-render was requested, and `AGENTS.md` matches its recorded output hash
- **THEN** `AGENTS.md` is re-rendered by default all the same, and the other rendered files stay unchanged

#### Scenario: Breaking release, owner declines
- **WHEN** the template for `AGENTS.md` changed and the owner declines the re-render
- **THEN** `AGENTS.md` is not written, the stamp keeps its old template hash, and the next dry run offers the re-render again

#### Scenario: Template unchanged
- **WHEN** the template for `AGENTS.md` equals the stamp's template hash and no re-render was requested
- **THEN** no rendered file is written, even when the update range holds a **BREAKING** entry or the rendering would differ

#### Scenario: Hand-edited file
- **WHEN** `AGENTS.md` differs from its recorded output hash
- **THEN** the file is not written, and the difference to a fresh rendering is shown as a proposal

#### Scenario: Output hash not recorded
- **WHEN** the stamp records `null` as the output hash of `AGENTS.md` and its template changed
- **THEN** the file is not written, the summary says it cannot be proven untouched, and a fresh rendering is shown as a proposal

#### Scenario: Proposal taken whole
- **WHEN** the owner replaces a `null`-hash `AGENTS.md` with the fresh rendering, commits it and plans again
- **THEN** the file is reported as current, `apply` records its output hash in the stamp, and a later change to its template re-renders it by default

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

In a git instance, an upgrade SHALL end in exactly one commit that holds only the
planned paths, the stamp and a newly tracked `.kb-onboard.json`; unrelated uncommitted
work SHALL stay uncommitted. Without git, the upgrade SHALL always create
`.kb-upgrade-backup/<version>-<UTC timestamp>/` before writing, copy there every file it
overwrites or deletes, add a `backup.json` with the versions and the hash before and
after of every path apply writes or deletes, and name that folder in its report.

#### Scenario: Git instance with unrelated work in progress
- **WHEN** an upgrade is applied while an unrelated note has uncommitted edits
- **THEN** one new commit holds the upgrade, and the note's edits remain uncommitted

#### Scenario: Instance without git
- **WHEN** an upgrade is applied in a folder that is not a git repository
- **THEN** every replaced or deleted file has a copy in the backup folder, `backup.json` lists every path apply wrote or deleted, added files included, and the report names that folder

#### Scenario: Adoption without git that replaces nothing
- **WHEN** an adoption without git only adds files and the stamp
- **THEN** the backup folder exists, its `backup.json` lists the added files and the stamp, and the folder the report names is that folder

### Requirement: Up-to-date instances and downgrades

brain-upgrade SHALL report "up to date" and change nothing when the source version equals
the stamp version, no owned file needs action, and no executable bit is missing. It SHALL
refuse a source version older than the stamp version.

#### Scenario: Already current
- **WHEN** the stamp and the source both say `0.2.0`, every owned file matches and every listed file has its executable bit
- **THEN** brain-upgrade reports that the instance is up to date and writes nothing

#### Scenario: Older source
- **WHEN** the stamp says `0.2.1` and the source is `0.2.0`
- **THEN** brain-upgrade refuses and changes nothing

### Requirement: The default path needs no flag and counts only its own download

When the owner names no source, the path from `fetch` through `plan`, `apply` and `commit`
SHALL work without `--allow-repository`. `plan` SHALL obtain the release by downloading it
itself over HTTPS from the repository in the stamp, at the version `fetch` reported. Only
such a download SHALL count as verified. A folder, a zip or a local clone SHALL count as
unverified, whoever saved it and whatever lies next to it, and SHALL need the owner's
consent at `fetch` and at `plan`.

#### Scenario: The skill's commands in order
- **WHEN** an instance with a stamp runs the commands of the skill's default path, in order, with no `--allow-repository`
- **THEN** `fetch`, `plan`, `apply` and `commit` all succeed, and the plan's source is a verified download of the version `fetch` reported

#### Scenario: Foreign zip without consent
- **WHEN** `--source` names a zip that claims the stamp's repository, at `fetch` or at `plan`, without `--allow-repository`
- **THEN** it is refused and nothing changes

#### Scenario: Foreign zip with a planted record
- **WHEN** that zip comes with a file next to it that claims a verification and carries the zip's correct hash
- **THEN** it is refused all the same, because nothing next to a source is read

#### Scenario: The saved archive passed back
- **WHEN** the archive `fetch` saved is passed to `plan --source` without `--allow-repository`
- **THEN** it is refused, nothing changes, and the message says how to have the release verified with `--to <version>`

#### Scenario: A named source the owner accepted
- **WHEN** the owner accepts a zip, folder or clone and `--allow-repository` names the repository it claims
- **THEN** `fetch` and `plan` proceed as before

### Requirement: The dry run compares the executable bit

For each file that the source ships as owned and lists as executable in its manifest, the
dry run SHALL compare the executable bit as well as the content. The current bit SHALL be
the mode in `HEAD` when git tracks the file, otherwise the file's mode on Linux and macOS.
A missing bit SHALL be a selected row, separate from the file's action, which the owner MAY
decline. Where there is no bit to read, nothing SHALL be planned.

#### Scenario: New mode with equal content
- **WHEN** a listed file has mode `100644` in `HEAD` and its content equals the source
- **THEN** the plan shows a selected row for the bit

#### Scenario: Base already past the update
- **WHEN** the stamp and the source name the same version, every owned file matches, and a listed file has mode `100644`
- **THEN** the instance is not reported as up to date, and the plan offers the bit

#### Scenario: File edited by the owner
- **WHEN** a listed file has local edits and the template did not change it
- **THEN** its action stays `keep (yours)`, its text stays, and the bit row is selected

#### Scenario: Owner declines the bit
- **WHEN** the owner declines the bit row
- **THEN** the mode stays as it was, and the next dry run offers it again

#### Scenario: Windows without git
- **WHEN** the instance is on Windows and is not a git repository
- **THEN** no row for the bit is planned

### Requirement: Apply and commit carry the executable bit

Writing a listed file SHALL give it the bit unless the owner declined it. `apply` SHALL set
the bit on disk where the filesystem has one, and the commit SHALL record mode `100755`. No
write SHALL drop a bit a file already has, and brain-upgrade SHALL NOT remove one.

#### Scenario: Row applied
- **WHEN** the owner keeps the bit row for a file with mode `100644`
- **THEN** after apply and commit the file has mode `100755` in `HEAD`, and `git status` shows no change for it

#### Scenario: File added by the update
- **WHEN** the plan adds a listed file
- **THEN** the commit records it with mode `100755`, and on Linux and macOS the file on disk is executable

#### Scenario: Update of a file that is already executable
- **WHEN** an update replaces the content of a file with mode `100755`, on Linux or macOS
- **THEN** the file on disk stays executable and `git status` shows no mode change

#### Scenario: Rollback
- **WHEN** apply fails after setting a bit
- **THEN** the rollback puts the earlier bit back

### Requirement: Edits that do not follow a rename are called out

When the plan keeps an edited file because the template removed its path, and the source
ships a file that is the same path with one folder renamed or inserted, the dry run SHALL
list both paths on a separate line that says the edits do not move to the new name. This
line SHALL NOT change what is written.

#### Scenario: Edited skill file under an old name
- **WHEN** `.claude/skills/lint/SKILL.md` was edited in the instance and the source ships `.claude/skills/brain-lint/SKILL.md` instead
- **THEN** the deletion is proposed unselected as before, and a separate line names the old and the new path

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
