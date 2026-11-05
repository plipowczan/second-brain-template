## ADDED Requirements

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

## RENAMED Requirements

- FROM: `### Requirement: Rendered files are re-rendered only on request and only if untouched`
- TO: `### Requirement: Rendered files are re-rendered on request, or after a breaking release, and only if untouched`

## MODIFIED Requirements

### Requirement: Rendered files are re-rendered on request, or after a breaking release, and only if untouched

brain-upgrade SHALL re-render `CLAUDE.md`, `AGENTS.md` and `content/WRITING_STYLE.md` when
the owner asks for it. It SHALL also re-render `AGENTS.md`, unless the owner declines, when
the `CHANGELOG.md` entries of the update range hold a **BREAKING** entry. It SHALL NOT
re-render `CLAUDE.md` or `content/WRITING_STYLE.md` by default. It SHALL use the source's
templates and `.kb-onboard.json`, and SHALL write the result only if the local file still
matches the output hash in the stamp. A `null` output hash never matches. In every other
case it SHALL show the difference as a proposal and leave the file unchanged.

#### Scenario: Untouched file, re-render requested
- **WHEN** the owner requests a re-render and `AGENTS.md` matches its recorded output hash
- **THEN** `AGENTS.md` is rewritten from the new template and the stamp records the new hashes

#### Scenario: Breaking release, untouched file
- **WHEN** the update range holds a **BREAKING** entry, no re-render was requested, and `AGENTS.md` matches its recorded output hash
- **THEN** the plan says `AGENTS.md` will be re-rendered and why, and without a refusal it is rewritten, while `content/WRITING_STYLE.md` and `CLAUDE.md` stay unchanged

#### Scenario: Breaking release, owner declines
- **WHEN** the update range holds a **BREAKING** entry and the owner declines the re-render
- **THEN** `AGENTS.md` is not written

#### Scenario: No breaking entry
- **WHEN** the update range holds no **BREAKING** entry and no re-render was requested
- **THEN** no rendered file is written

#### Scenario: Hand-edited file
- **WHEN** `AGENTS.md` differs from its recorded output hash
- **THEN** the file is not written, and the difference to a fresh rendering is shown as a proposal

#### Scenario: New placeholder without a value
- **WHEN** the new template uses a placeholder that `.kb-onboard.json` has no value for
- **THEN** the owner is asked for the value, it is saved to `.kb-onboard.json`, and the render proceeds

#### Scenario: Render inputs missing
- **WHEN** `.kb-onboard.json` does not exist
- **THEN** rendered files are only reported as proposals

### Requirement: The update source works without git and offline

brain-upgrade SHALL accept as its source:

- a local directory (a template clone or an unpacked release);
- a local release `.zip`;
- when neither is given, a release archive downloaded over HTTPS from the repository
  recorded in the stamp. `--to <version>` selects the version, and the latest GitHub
  Release is the default.

Downloading SHALL NOT require git. Once the source is local, planning SHALL NOT require
network access. A local source SHALL need the owner's consent, because it cannot prove
where it comes from.

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
