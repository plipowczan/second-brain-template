## ADDED Requirements

### Requirement: Codex skill copies are generated from the Claude skills

Skills SHALL be edited only in `.claude/skills/`. The template SHALL contain an
author-class tool that writes, for every skill directory under `.claude/skills/` that
ships, a copy under `.agents/skills/<skill>/`. A copy SHALL hold the skill's `SKILL.md`
and its other Markdown files at the same relative paths, byte for byte, and SHALL NOT
hold scripts or other files.

#### Scenario: Contributor changes a skill
- **WHEN** a contributor edits `.claude/skills/brain-qa/SKILL.md` and runs the tool
- **THEN** `.agents/skills/brain-qa/SKILL.md` equals the source byte for byte, and no other copy changes

#### Scenario: Scripts stay in one place
- **WHEN** the tool writes the copy of `brain-reindex`
- **THEN** the copy has no `scripts/` folder, and its `SKILL.md` still runs `python .claude/skills/brain-reindex/scripts/build_indexes.py`

#### Scenario: Onboarding copy is not rewritten
- **WHEN** the tool writes the copy of `brain-onboard`
- **THEN** the copy still renders `CLAUDE.md` from `CLAUDE.template.md` and `AGENTS.md` from `AGENTS.template.md`

#### Scenario: Frontmatter Codex cannot read
- **WHEN** a source `SKILL.md` has frontmatter that is not valid YAML, an empty `description`, a `description` over 1024 characters or a `name` over 64 characters
- **THEN** the tool exits non-zero and names the skill and the field

#### Scenario: A skill refers to a file the copy does not have
- **WHEN** a source `SKILL.md` names `scripts/x.py` without the `.claude/skills/<skill>/` prefix
- **THEN** the tool exits non-zero and names the skill and the path

### Requirement: The check fails on a copy that drifted

The tool SHALL have a check mode that writes nothing and exits non-zero, naming each path,
when a copy differs from its source, a skill has no copy, or `.agents/skills/` holds a
copy or a file with no source. The template's test suite SHALL run the check, so it runs
in CI on Linux and Windows.

#### Scenario: Source edited, copy not regenerated
- **WHEN** a contributor edits a source `SKILL.md`, does not run the tool, and runs `tests/run_tests.py`
- **THEN** the run fails and names the stale copy

#### Scenario: Leftover wrapper skill
- **WHEN** `.agents/skills/source-command-b-qa/SKILL.md` is tracked and no `.claude/skills/source-command-b-qa/` exists
- **THEN** the check exits non-zero and names the path

#### Scenario: Line endings do not count as drift
- **WHEN** a Windows checkout has CRLF in a copy and its source, while git stores both with LF
- **THEN** the check passes

### Requirement: No wrappers for slash commands

The template SHALL NOT ship skills under `.agents/skills/` that only wrap a command from
`.claude/commands/`. The documentation SHALL say how to start a skill by name in Codex.

#### Scenario: Copies match the skills one to one
- **WHEN** the check runs on a release
- **THEN** every directory under `.agents/skills/` has a directory of the same name under `.claude/skills/`

### Requirement: The Codex session hook works in any clone

The template SHALL ship `.codex/hooks.json` with a SessionStart hook that runs the same
script as the Claude Code SessionStart hook, `.claude/hooks/load_vault_map.py`. The hook
command SHALL NOT contain an absolute path, and the template SHALL NOT ship a second copy
of the hook script.

#### Scenario: Base cloned elsewhere
- **WHEN** a base is cloned to any folder, the owner trusts it and approves the hook in Codex, and a Codex session starts in its root
- **THEN** the hook prints the base's `content/_indexes/vault-map.md`, on Windows and on Linux or macOS

#### Scenario: Base without git
- **WHEN** a base was downloaded as a ZIP and a Codex session starts in its root
- **THEN** the hook runs the same way, because its command needs no git

#### Scenario: Absolute path in the hook
- **WHEN** a contributor puts an absolute path in `.codex/hooks.json` and runs the check
- **THEN** the check exits non-zero and names the hook

#### Scenario: Claude Code is unaffected
- **WHEN** a Claude Code session starts in a base that has `.codex/hooks.json`
- **THEN** the session hook from `.claude/settings.json` behaves as before
