# Spec Delta

## Purpose

Lets an owner use a base's skills and its session hook in Codex, while every skill is
still written in one place, `.claude/skills/`. The Codex files are generated and checked
in the template, and they reach bases like any other template file.

## ADDED Requirements

### Requirement: Codex skill stubs are generated from the Claude skills

Skills SHALL be edited only in `.claude/skills/`. The template SHALL contain an
author-class generator that writes a stub at `.agents/skills/<skill>/SKILL.md` for every
skill directory under `.claude/skills/` whose `SKILL.md` the manifest ships. A stub SHALL
hold the source's frontmatter lines unchanged and a fixed body that tells the agent to
read and follow `.claude/skills/<skill>/SKILL.md`, naming that folder as the skill's base
directory. `.agents/skills/<skill>/` SHALL hold no other file.

#### Scenario: Contributor edits a skill's text
- **WHEN** a contributor edits the body of `.claude/skills/brain-qa/SKILL.md` and runs the generator
- **THEN** no file under `.agents/skills/` changes

#### Scenario: Contributor edits a skill's description
- **WHEN** a contributor edits the `description` of `.claude/skills/brain-qa/SKILL.md` and runs the generator
- **THEN** the frontmatter of `.agents/skills/brain-qa/SKILL.md` equals the source's, and no other stub changes

#### Scenario: Scripts stay in one place
- **WHEN** the generator writes the stub of `brain-reindex`
- **THEN** `.agents/skills/brain-reindex/` holds only `SKILL.md`, and the stub names `.claude/skills/brain-reindex/SKILL.md`, whose commands run `python .claude/skills/brain-reindex/scripts/build_indexes.py`

### Requirement: The check fails on a Codex file the generator would not write

The generator SHALL have a check mode that writes nothing and exits non-zero, naming each
path, when a stub or `.codex/hooks.json` differs from what the generator would write
(line endings aside) or is missing, or when `.agents/skills/` holds a directory or file
with no source skill, apart from paths the manifest excludes. The template's test suite
SHALL run the check, so it runs in CI on Linux and Windows.

#### Scenario: Description edited, stub not regenerated
- **WHEN** a contributor edits a source `description`, does not run the generator, and runs `tests/run_tests.py`
- **THEN** the run fails and names the stale stub

#### Scenario: A skill without a stub
- **WHEN** a new skill directory is added under `.claude/skills/` and the generator is not run
- **THEN** the check exits non-zero and names the missing stub

#### Scenario: Leftover wrapper skill
- **WHEN** `.agents/skills/source-command-b-qa/SKILL.md` exists, tracked or not, and no `.claude/skills/source-command-b-qa/` exists
- **THEN** the check exits non-zero and names the path

#### Scenario: Hand-edited hook
- **WHEN** a contributor puts an absolute path into `.codex/hooks.json` and runs the check
- **THEN** the check exits non-zero and names `.codex/hooks.json`

### Requirement: Source frontmatter is read whole

The check SHALL also exit non-zero, naming the skill and the field, when a source
frontmatter is not valid YAML, lacks a string `name` or `description`, or YAML reads less
of the description than the file holds. Write mode SHALL write nothing in that case.

#### Scenario: Description cut by a comment
- **WHEN** a source `description` is unquoted and contains ` #`
- **THEN** the check exits non-zero and names the skill and the field

#### Scenario: Frontmatter that is not YAML
- **WHEN** a source frontmatter is not valid YAML, or has no `description`
- **THEN** the check exits non-zero and names the skill and the field, and write mode writes nothing

### Requirement: Codex users start skills by name

The template SHALL NOT ship skills under `.agents/skills/` that only wrap a command from
`.claude/commands/`. `ENVIRONMENTS.md` SHALL say how to start a skill by name in Codex,
and `AGENTS.template.md` SHALL tell an agent without slash commands that `/b:<name>`
means the `brain-<name>` skill.

#### Scenario: Stubs match the skills one to one
- **WHEN** the check passes on a release
- **THEN** every directory under `.agents/skills/` has a directory of the same name under `.claude/skills/`, and every shipped skill has a stub

### Requirement: The Codex session hook works in the root of any clone

The template SHALL ship `.codex/hooks.json`, written by the generator, with one
SessionStart hook that runs `python .claude/hooks/load_vault_map.py`, the same script as
the Claude Code SessionStart hook. The hook command SHALL NOT contain an absolute path,
and the template SHALL NOT ship a second copy of the hook script.

#### Scenario: Base cloned elsewhere
- **WHEN** a base is cloned to any folder, the owner trusts it and approves the hook in Codex, and a Codex session starts in its root
- **THEN** the hook prints the base's `content/_indexes/vault-map.md`, on Windows and on Linux or macOS

#### Scenario: Base without git
- **WHEN** a base was downloaded as a ZIP, the owner trusts it and approves the hook, and a Codex session starts in its root
- **THEN** the hook prints the base's `content/_indexes/vault-map.md`

#### Scenario: Claude Code is unaffected
- **WHEN** a Claude Code session starts in a base that has `.codex/hooks.json`
- **THEN** the session hook from `.claude/settings.json` behaves as before

### Requirement: A base that ran Codex's migration upgrades after one cleanup step

The changelog entry and `ENVIRONMENTS.md` SHALL tell the owner of a base that ran Codex's
`/import` what to delete before upgrading: `.agents/skills/<skill>/` for each template
skill and `.codex/hooks.json` (required), and every `.agents/skills/source-command-*`,
`.codex/hooks/` and `.codex/agents/` (advised). The owner's own skills under
`.agents/skills/` SHALL stay.

#### Scenario: Upgrade after the cleanup
- **WHEN** a base holds untracked migration output at the template's new paths, and the owner deletes it as the changelog entry says, keeping their own `.agents/skills/my-skill/`
- **THEN** `/b:upgrade` applies and commits, every stub under `.agents/skills/` equals the template's, and `my-skill` is unchanged
