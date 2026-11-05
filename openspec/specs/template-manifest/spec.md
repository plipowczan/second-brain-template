# template-manifest Specification

## Purpose
Defines which files of the template reach an instance and how each class of file behaves
when an instance is created and when it is updated.

## Requirements

### Requirement: The manifest declares four file classes

The template SHALL contain a root file `.kb-manifest.json`, readable with the Python
standard library alone. It SHALL declare:

- the manifest format number, the template version and the source repository;
- glob patterns for the **owned**, **seeded** and **author** classes;
- for the **rendered** class, a map from each output path to its `*.template.md` source;
- an `exclude` list of files that never ship.

A file in a template tree SHALL be classified by the first class that matches it, in the
order author, rendered, owned, seeded. A file that matches `exclude`, or no class at all,
SHALL never be shipped.

#### Scenario: Manifest is read without third-party packages
- **WHEN** a script that imports only the Python standard library reads `.kb-manifest.json`
- **THEN** it obtains the format, the version, the repository, the four classes and the exclude list

#### Scenario: Stray file in a source directory is not shipped
- **WHEN** an update source directory contains `graft/cache.bin`, `.claude/settings.local.json` or a `__pycache__/` folder
- **THEN** none of them is copied to the instance, and the dry run lists any file that matches no class as ignored

### Requirement: Every tracked template file has a class

The template's manifest check SHALL fail when a file tracked in the template repository
matches no class, and it SHALL name that file.

#### Scenario: New file without a class
- **WHEN** a contributor adds a tracked file at the repository root that no pattern matches and runs the manifest check
- **THEN** the check exits non-zero and names the file

### Requirement: Ownership inside an instance is decided by concrete paths

Inside an instance, brain-upgrade SHALL treat a file as template-owned only if its path
is one of these:

- a file the source version ships in the owned class;
- a path recorded in the instance stamp;
- a path in the template's history index.

Class patterns SHALL NOT claim instance files.

#### Scenario: The instance's own skill is left alone
- **WHEN** an instance has `.claude/skills/my-skill/SKILL.md`, a path that no template version ever shipped
- **THEN** brain-upgrade neither changes nor deletes it, and does not list it as a template file

### Requirement: Seeded files belong to the instance

The seeded class SHALL contain `content/**` and `README.md`. brain-upgrade SHALL NOT
create, change or delete seeded files. When the new version changes or adds seeded files,
the dry run SHALL list them as information only.

#### Scenario: Starter template changed upstream
- **WHEN** the new version changes `content/templates/book.md`
- **THEN** the instance's copy stays as it is, and the dry run lists the change as information

#### Scenario: Template README changed upstream
- **WHEN** the new version changes `README.md`
- **THEN** the instance's `README.md` stays as it is, no question is asked, and the dry run lists the change as information

#### Scenario: New starter file upstream
- **WHEN** the new version adds a file under `content/`
- **THEN** brain-upgrade does not create it in the instance, and the dry run lists it as information

### Requirement: Author files never reach an instance

The author class SHALL contain at least `openspec/**`, `CONTRIBUTING.md`, `CLAUDE.local.md`
and `dev/**`. Author files SHALL be excluded from every source archive of the template,
SHALL never be copied by brain-upgrade, and SHALL be deleted by onboarding.

#### Scenario: Download ZIP and release archives
- **WHEN** a ZIP or release archive of the template is produced with `git archive` (as GitHub does)
- **THEN** it contains no author-class file

#### Scenario: Upgrade from a full local clone
- **WHEN** the update source is a local clone that contains `openspec/` and `CONTRIBUTING.md`
- **THEN** neither is copied to the instance

#### Scenario: Onboarding a fresh clone
- **WHEN** `/b:onboard` completes in a fresh clone of the template
- **THEN** every author-class file that came with the clone has been deleted

#### Scenario: Pristine leftover in an older instance
- **WHEN** an instance contains `CONTRIBUTING.md` whose content matches a version the template shipped
- **THEN** the dry run proposes deleting it, and an author-class file whose content matches no shipped version is left alone

### Requirement: Onboarding refuses to run in the template source

`/b:onboard` SHALL stop before changing any file when `CLAUDE.local.md` exists in the
repository root, and SHALL explain that the checkout looks like the template source.

#### Scenario: Onboard started in the author's checkout
- **WHEN** `/b:onboard` starts in a checkout that has `CLAUDE.local.md`
- **THEN** no file is rendered, deleted or created, and the user is told to try onboarding in a scratch clone

### Requirement: The manifest lists the files shipped as executable

`.kb-manifest.json` MAY contain an `executable` list of paths. It SHALL be the only source
of the executable bit for brain-upgrade, for every kind of update source. A path that
belongs to the base (under `content/`, `README.md`, the stamp, `.kb-onboard.json`) SHALL
stop the source.

#### Scenario: Same answer on every source
- **WHEN** the same release is read from the GitHub archive, a zip rebuilt without mode information, a folder on Windows and a clone
- **THEN** brain-upgrade treats the same files as executable

#### Scenario: A note listed as executable
- **WHEN** a source's manifest lists a path under `content/`
- **THEN** brain-upgrade stops, says why, and changes nothing

#### Scenario: Engine that does not know the list
- **WHEN** an engine from before this requirement reads a manifest with `executable`
- **THEN** it ignores the key and works as before

### Requirement: The manifest check covers the executable list

The template's manifest check SHALL fail when a file with mode `100755` in the git index is
not in the `executable` list, and when a listed file is not tracked with that mode. It SHALL
name the file.

#### Scenario: New executable file not listed
- **WHEN** a contributor tracks a file with mode `100755` that the list does not name, and runs the manifest check
- **THEN** the check exits non-zero and names the file

#### Scenario: Listed file without the mode
- **WHEN** the list names a file tracked with mode `100644`, and the manifest check runs
- **THEN** the check exits non-zero and names the file
