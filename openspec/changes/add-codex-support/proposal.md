# Proposal

## Why

The template promises support for agents other than Claude Code. `README.md` ("Works
beyond Claude Code") and `ENVIRONMENTS.md` name Codex, and `AGENTS.md` is the instruction
file Codex reads. But the template ships nothing else Codex reads: no skills where Codex
looks for them, no session hook. An owner who works in Codex gets the instructions and
none of the workflows.

Codex has an import command, `/import` (Settings → Import in the app), that converts a
Claude Code project. On 2026-10-15 the maintainer ran it in this repository's checkout.
Below, that run is "the migration", and what it wrote is "the migration output": two
untracked folders, `.agents/` and `.codex/`. Checked on 2026-11-09, the output is not fit
to ship:

- **Blind text replacement broke the skill copies in `.agents/skills/`.** `.claude` became
  `.Codex`, so every script call points at a folder that exists nowhere
  (`python .Codex/skills/brain-reindex/scripts/build_indexes.py`). `CLAUDE.md` became
  `AGENTS.md`, so the `brain-onboard` copy looks for `Codex.template.md` and renders
  `AGENTS.md` twice and `CLAUDE.md` not at all.
- **The copies are already stale.** The `brain-upgrade` copy still prescribes
  `plan --source`, the option PR #14 replaced with a download from GitHub, and lacks two
  test files added since.
- **The hook works on one machine only.** `.codex/hooks.json` runs the hook script by an
  absolute Windows path into the maintainer's checkout, which no other clone has.
- **19 `source-command-b-*` skills add nothing.** Each wraps one `/b:*` command, and each
  command only names a skill.

None of it was committed. `dev/check_manifest.py` fails on a tracked file that matches no
class, so the output could not have passed the tests.

Paweł, the maintainer, decided on 2026-11-09 to support Codex with files of its own
(option A of the issue `PL-550`), with the design reviewed before any implementation.

## What Changes

- **One source for every skill.** Skills are edited only in `.claude/skills/`. For each
  skill, a stub at `.agents/skills/<skill>/SKILL.md`, where Codex looks, holds the
  source's frontmatter unchanged and one fixed instruction: read and follow
  `.claude/skills/<skill>/SKILL.md`. Codex lists the skill from the frontmatter, and the
  agent reads the same file Claude Code reads. Scripts, references and skill text stay
  in one place.
- **A generator writes the Codex files.** `dev/build_codex_files.py` (the generator) writes
  every stub and `.codex/hooks.json`. Its `--check` mode (the check) fails on a Codex file
  that differs from what the generator writes or is missing, on a file under
  `.agents/skills/` with no source skill, and on a source frontmatter that YAML does not
  read whole. `tests/run_tests.py` runs the check, so the `Tests` workflow runs it on
  Linux and Windows.
- **Two broken frontmatters are fixed at the source.** On `main`, a ` #` in the
  `brain-export` description makes YAML read the rest as a comment (49 of 452 characters
  survive), and a `: ` makes the `brain-ingest` frontmatter invalid YAML. Both
  descriptions are quoted. The `brain-export` and `brain-import` descriptions say
  `/b:import` and `/b:export` instead of `/import` and `/export`, because in Codex
  `/import` is the migration command.
- **No command wrappers.** In Codex a skill is started by name (`$brain-ingest`) or from
  `/skills`. `ENVIRONMENTS.md` says so, and `AGENTS.md` gets one sentence: an agent
  without slash commands treats `/b:<name>` as the `brain-<name>` skill.
- **A session hook that works in the root of any clone.** `.codex/hooks.json` runs the
  same `.claude/hooks/load_vault_map.py` that Claude Code runs, by a relative path. Bash,
  PowerShell, Windows PowerShell and cmd read that path the same way, and it needs no
  git. It works when Codex starts in the base's root folder. There is no second copy of
  the hook script. Each clone needs two one-time steps before Codex runs the hook: the
  owner trusts the project, then approves the hook in `/hooks`. `ENVIRONMENTS.md` names
  both.
- **The new paths ship as template files.** `.agents/skills/**` and `.codex/hooks.json`
  join the owned class in `.kb-manifest.json`, so a new base gets them with the clone and
  an existing base with `/b:upgrade`. Any other file under `.agents/` or `.codex/` still
  matches no class, so `dev/check_manifest.py` keeps failing on it.
- **Docs and changelog.** `ENVIRONMENTS.md` and `README.md` say what works in Codex and
  what to switch on there. `AGENTS.template.md` gets the sentence above. `CONTRIBUTING.md`
  names the generator and the rule: edit the source, run the generator. A `CHANGELOG.md`
  entry gets an "Existing bases" paragraph.
- **A short trial in real Codex comes first.** Before any code, two hand-written stubs and
  the hook are tried in a scratch clone (tasks 0.2-0.5). If Codex does not follow a stub,
  the design falls back to full copies of the skill text (D3 in `design.md`), and Paweł
  is asked again.
- **The migration output goes.** It is deleted from the maintainer's checkout after a copy
  is saved for the upgrade test (task 0.1). Nothing needs removing from git: the folders
  were never committed.

No breaking change. Claude Code behaves the same: the upgrade adds small files it does
not read.

## Non-goals

- Codex versions of `.claude/agents/` (the migration also converted `web-search-agent.md`
  to `.codex/agents/web-search-agent.toml`, with broken paths).
- Native files for Copilot, Cursor or Antigravity.
- Regenerating Codex files inside a base. `dev/` never ships. A stub changes only when its
  skill's frontmatter does; an owner who adds a skill or edits a description writes the
  stub by hand (see Open Questions in `design.md`).
- Rewriting skills for Codex's tool names (`AskUserQuestion`, `Task`). D4 in `design.md`
  says what Codex does instead.

## Capabilities

### New Capabilities

- `codex-support`: the generated Codex skill stubs and session hook, their check, and the
  upgrade of a base that ran the migration.

### Modified Capabilities

- `template-manifest`: `.agents/skills/**` and `.codex/hooks.json` are template-owned.

## Impact

- **Code:** new `dev/build_codex_files.py` and `dev/test_build_codex_files.py`; one more
  call in `tests/run_tests.py`. The hook script stays as it is (D5 in `design.md`).
- **Generated files:** one stub per skill (`.agents/skills/<skill>/SKILL.md`, 21 on
  `main`) and `.codex/hooks.json`.
- **Source skills:** the `brain-export` and `brain-ingest` descriptions are quoted; the
  `brain-export` and `brain-import` descriptions name `/b:import` and `/b:export`. No
  skill body changes.
- **Data:** `.kb-manifest.json` gains two owned patterns; `known-hashes.json` picks the
  new files up at the next release.
- **Docs:** `ENVIRONMENTS.md`, `README.md`, `AGENTS.template.md`, `CONTRIBUTING.md`,
  `CHANGELOG.md`.
- **Bases:** at the next upgrade, one new file per template skill plus
  `.codex/hooks.json`, none of them in `content/`, and three updated skills. `AGENTS.md`
  gets the new sentence only when the owner re-renders it.
