# Proposal

## Why

The template promises more than Claude Code. `README.md` ("Works beyond Claude Code") and
`ENVIRONMENTS.md` name Codex, and `AGENTS.md` is the instruction file Codex reads. But the
template ships nothing else Codex reads: no skills where Codex looks for them, no session
hook. A Codex user gets the instructions and none of the workflows.

The only attempt so far makes the case for doing it properly. On 2026-10-15 Codex's own
migration ran in the maintainer's checkout and left two untracked folders, `.agents/` and
`.codex/`. Checked on 2026-11-09, they are not fit to ship:

- **Blind text replacement broke the copies.** `.claude` became `.Codex`, so every script
  call points at a folder that exists nowhere
  (`python .Codex/skills/brain-reindex/scripts/build_indexes.py`). `CLAUDE.md` became
  `AGENTS.md`, so the `brain-onboard` copy looks for `Codex.template.md` and renders
  `AGENTS.md` twice instead of `CLAUDE.md` once.
- **The copies are already stale.** The `brain-upgrade` copy still prescribes
  `plan --source`, the path PR #14 replaced, and lacks two test files added since.
- **The hook works on one machine only.** `.codex/hooks.json` runs the hook script by
  an absolute Windows path into the maintainer's checkout, which no other clone has.
- **19 `source-command-b-*` skills only wrap the `/b:*` commands**, which already just
  name a skill.

The manifest classifies none of these paths, so a single `git add -A` would send them to
every base at the next release.

Paweł decided on 2026-11-09 to support Codex properly (option A of `PL-550`), with the
design reviewed before any implementation.

## What Changes

- **One source for every skill.** Skills are edited only in `.claude/skills/`. An author
  tool, `dev/build_codex_skills.py`, writes the copies Codex reads to `.agents/skills/`.
  A copy holds what the agent reads (`SKILL.md` and the skill's other Markdown files),
  byte for byte. It holds no scripts: every skill already calls its scripts by their
  path under `.claude/skills/`, which exists in every base, so code and tests stay in one
  place.
- **No text is rewritten.** The migration showed what replacing `CLAUDE.md` or `.claude`
  does. A base has both `CLAUDE.md` and `AGENTS.md`, and `.claude/skills/` is where the
  scripts are, so the copies are correct as they are.
- **CI catches a stale copy.** `dev/build_codex_skills.py --check` fails on a copy that
  differs from its source, a skill without a copy, or a copy without a skill.
  `tests/run_tests.py` runs it, so the `Tests` workflow checks it on Ubuntu and Windows.
- **No command wrappers.** In Codex a skill is called by name (for example
  `$brain-ingest`). The docs say so; no `source-command-*` skills ship.
- **A session hook that works in any clone.** `.codex/hooks.json` runs the same
  `.claude/hooks/load_vault_map.py` that Claude Code runs, by a relative path that works
  in every shell and without git. There is no second copy of the hook script. Codex runs a
  project hook only after the owner trusts the project and approves the hook in `/hooks`,
  once per clone; the docs say so.
- **The new paths ship as template files.** `.agents/**` and `.codex/**` join the owned
  class in `.kb-manifest.json`, so a new base gets them with the clone and an existing
  base with `/b:upgrade`.
- **Docs and changelog.** `ENVIRONMENTS.md` and `README.md` say what works in Codex and
  what to switch on there. `CONTRIBUTING.md` names the generator and the rule: edit the
  source, run the tool. A `CHANGELOG.md` entry with an "Existing bases" paragraph.
- **The migration output goes.** The untracked `.agents/` and `.codex/` in the
  maintainer's checkout are deleted once the generated files replace them. Nothing to
  remove from git: they were never committed.

No breaking change. Nothing changes for Claude Code users.

## Non-goals

- Codex versions of `.claude/agents/` (the migration also converted
  `web-search-agent.md` to `.codex/agents/web-search-agent.toml`, with broken paths).
- Native files for Copilot, Cursor or Antigravity.
- Regenerating copies inside a base. `dev/` never ships; an owner who edits a skill and
  uses Codex copies the file by hand (see Open questions in `design.md`).
- Translating Claude Code tool names inside skills (`AskUserQuestion`, `Task`). Codex
  asks in the chat instead.

## Capabilities

### New Capabilities

- `codex-support`: generated skill copies for Codex, their check, the Codex session hook.

### Modified Capabilities

- `template-manifest`: the Codex paths are template-owned.

## Impact

- **Code:** new `dev/build_codex_skills.py` and its tests; one more call in
  `tests/run_tests.py`. The hook script stays as it is (D5 in `design.md`).
- **Generated files:** `.agents/skills/<skill>/SKILL.md` for each of the 20 skills, plus
  the Markdown references of `excalidraw-diagram`; `.codex/hooks.json`.
- **Source skills:** a few descriptive mentions of `scripts/...` without the
  `.claude/skills/<skill>/` prefix become full paths, so the copies don't point at a
  folder they don't have. The `brain-ingest` description gets quotes: today it is not
  valid YAML.
- **Data:** `.kb-manifest.json` gains two owned patterns; `known-hashes.json` picks the
  new files up at the next release.
- **Docs:** `ENVIRONMENTS.md`, `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`.
- **Instances:** about 25 new files at the next upgrade, none of them in `content/`.
