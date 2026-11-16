## ADDED Requirements

### Requirement: Codex files are template-owned

The owned class SHALL cover `.agents/skills/**` and `.codex/hooks.json`, and no other path
under `.agents/` or `.codex/`. The generated skill stubs and `.codex/hooks.json` SHALL
reach a new base with the clone and an existing base through `brain-upgrade`, like any
owned file.

#### Scenario: Existing base upgrades to the release that adds them
- **WHEN** a base on an earlier release runs `/b:upgrade` to the release that adds `.agents/skills/` and `.codex/hooks.json`
- **THEN** the plan adds them as new template files, and nothing under `content/` changes

#### Scenario: Another Codex file is committed in the template
- **WHEN** a contributor commits `.codex/config.toml` or `.codex/agents/web-search-agent.toml` to the template
- **THEN** `dev/check_manifest.py` fails and names the file, because it matches no class
