## ADDED Requirements

### Requirement: Codex files are template-owned

The owned class SHALL cover `.agents/**` and `.codex/**`. The generated skill copies and
the Codex hook SHALL reach a new base with the clone and an existing base through
brain-upgrade, like any owned file. Paths in those folders that no template version
shipped SHALL stay the base's own.

#### Scenario: Existing base upgrades to the release that adds them
- **WHEN** a base on an earlier release runs `/b:upgrade` to the release that adds `.agents/skills/` and `.codex/hooks.json`
- **THEN** the plan adds them as new template files, and nothing under `content/` changes

#### Scenario: The base's own Codex skill
- **WHEN** a base has `.agents/skills/my-skill/SKILL.md`, a path no template version shipped
- **THEN** brain-upgrade neither changes nor deletes it

#### Scenario: Migration output in the template source
- **WHEN** a file under `.agents/skills/` that the generator did not write exists in the template checkout, tracked or not
- **THEN** the generator's check exits non-zero and names it, so it cannot be committed by accident
