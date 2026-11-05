## ADDED Requirements

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
