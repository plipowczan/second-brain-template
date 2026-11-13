# Design

## Context

Claude Code reads skills from `.claude/skills/<name>/SKILL.md`, slash commands from
`.claude/commands/`, and its session hook from `.claude/settings.json`, which runs
`python "$CLAUDE_PROJECT_DIR/.claude/hooks/load_vault_map.py"`. Codex reads `AGENTS.md`
and looks for skills and hooks elsewhere (D2, D5). Today the template ships only
`AGENTS.md` for it.

What exists, checked on 2026-11-09 in the maintainer's checkout (untracked, created by
Codex's migration on 2026-10-15):

| Path | Content | State |
|------|---------|-------|
| `.agents/skills/brain-*`, `excalidraw-diagram` | 20 copies of the skills, scripts and tests included | Every `.claude` became `.Codex` and every `CLAUDE` became `AGENTS` or `Codex`: script paths that exist nowhere, `brain-onboard` renders `AGENTS.md` twice and looks for `Codex.template.md`. Stale since PR #14: `brain-upgrade` still says `plan --source`, two test files missing. |
| `.agents/skills/source-command-b-*` | 19 skills of one line each: "Use the `brain-qa` skill …" | Wrappers of `.claude/commands/b/*.md`, which are already one-line pointers to a skill. |
| `.codex/hooks.json` | SessionStart runs `python '<absolute path of the checkout>\.codex\hooks\load_vault_map.py'` | Absolute path: works in this one folder only. |
| `.codex/hooks/load_vault_map.py` | Byte-identical to `.claude/hooks/load_vault_map.py` | A second copy of the same script. |
| `.codex/agents/web-search-agent.toml` | `.claude/agents/web-search-agent.md` converted | Points at `.Codex/agents/web-search-modules/`. |

Facts about the skills that shape the design:

- Every command in a `SKILL.md` calls its script by the repository-root path
  (`python .claude/skills/brain-lint/scripts/lint_scan.py`). Those paths exist in every
  base, so a copy elsewhere can call the same scripts.
- A few descriptive lines name a script relative to the skill (`scripts/bundle.py` in the
  `brain-export` table, `scripts/build_indexes.py` and `scripts/upgrade.py` in prose).
- Only `excalidraw-diagram` reads files next to its `SKILL.md`: `README.md` and three
  Markdown files under `references/`. It runs its renderer from
  `.claude/skills/excalidraw-diagram/references`, a repository-root path.
- 22 lines in the skills mention `CLAUDE.md`. In a base, `CLAUDE.md` exists and is a
  pointer to `AGENTS.md`, so the mentions hold for Codex too. In `brain-onboard` and
  `brain-upgrade` `CLAUDE.md` means that very file, which must be rendered.
- Frontmatter: all 20 skills have `name` and `description`; the five `brain-research*`
  skills also have `allowed-tools` and `user-invocable`.

## Goals / Non-Goals

**Goals:**

- A Codex user of a base gets the same 20 skills, in the same version as Claude Code.
- One place to edit a skill. A stale copy fails CI before it can ship.
- The session hook works in every clone, wherever it lives.
- What the migration left in the maintainer's checkout is replaced, not shipped.

**Non-Goals:**

- Codex agents converted from `.claude/agents/`.
- Native files for Copilot, Cursor, Antigravity.
- Regenerating copies inside a base.
- Rewriting skills for Codex's tool names.

## Decisions

### D1. The copies are generated, by an author tool in `dev/`

`dev/build_codex_skills.py` writes `.agents/skills/` from `.claude/skills/`. Like
`dev/build_known_hashes.py`, it has a `--check` mode that writes nothing and exits
non-zero with the paths that differ. `tests/run_tests.py` runs the check where `dev/`
exists, next to `dev/check_manifest.py`, so the `Tests` workflow runs it on Ubuntu and
Windows for every pull request.

The check fails when:

- a copy differs from its source (compared after normalising line endings, like the
  stamp hashes, so a Windows checkout does not fail);
- a skill under `.claude/skills/` has no copy;
- `.agents/skills/` holds a directory or file with no source (this catches the
  `source-command-*` wrappers and any leftover file of the migration);
- a source `SKILL.md` names `scripts/…` or another non-Markdown file of its skill
  without the `.claude/skills/<skill>/` prefix (D3);
- a source frontmatter is not valid YAML, or its `name` or `description` is outside
  Codex's limits (D4);
- `.codex/hooks.json` holds an absolute path or a command other than the one in D5.

*Alternatives considered.* Symlinks from `.agents/skills` to `.claude/skills`: git on
Windows checks them out as small text files unless symlinks are enabled, and "Download
ZIP" drops them, while the README promises a base works from a ZIP. A config key that
points Codex at `.claude/skills/`: see D2. A copy step in the release process only:
copies would drift between releases and nothing would say so.

### D2. Where Codex looks: `.agents/skills/` in the repository

Checked on 2026-11-09 against the Codex docs (`developers.openai.com/codex/*` now
redirects to `learn.chatgpt.com/docs/*`) and the `openai/codex` source at `0598a96e`
(latest release `rust-v0.167.0`, 2026-11-06):

- Codex scans `.agents/skills/` in every folder from the project root (found by `.git`)
  down to the session's folder, plus `~/.agents/skills/` and the system locations
  ([build-skills](https://learn.chatgpt.com/docs/build-skills)).
- It does not read `.claude/skills/`, and no `config.toml` key adds a skill folder. The
  only extra-root mechanism is an app-server call for client integrators.
- A project `.codex/skills/` also works, but only the source shows it, so the template
  uses the documented `.agents/skills/`.
- Repository skills load without the project trust that hooks need (source only).

So a copy in `.agents/skills/` is the only way, short of symlinks (D1).

### D3. A copy holds what the agent reads, not what it runs

For each skill, the copy holds `SKILL.md` and every other `*.md` file of the skill, at the
same relative path, byte for byte. Today that is 20 `SKILL.md` files plus the
`excalidraw-diagram` `README.md` and its three `references/*.md`. No scripts, tests,
`known-hashes.json` or renderer: the skills already call them by their path under
`.claude/skills/`, so one copy of the code serves both agents and its tests run once.

The few relative mentions of scripts (`scripts/bundle.py` in `brain-export`,
`scripts/build_indexes.py` in `brain-reindex`, `scripts/upgrade.py` in `brain-upgrade`)
become repository-root paths in the source skills. They would mislead a Codex agent
reading the copy, which has no `scripts/` folder. The generator's check then keeps it so.

*Alternative considered.* Copy the whole skill folder: 40-odd code files twice in every
base, two copies of each script that an owner can edit apart, and `known-hashes.json`
(the history index, the largest file in the template) twice.

### D4. No text is rewritten, frontmatter included

The copy equals its source. No `CLAUDE.md` → `AGENTS.md`, no `.claude` → anything. The
migration shows the cost: one blind replacement broke onboarding and every script call.
The mentions of `CLAUDE.md` are true in a base, which has both files.

Frontmatter stays as it is too: Codex ignores keys it does not know (`allowed-tools`,
`user-invocable`) without a warning. It needs a non-empty `description`, a `name` of at
most 64 characters, and shows the model at most 1024 characters of a description. The 20
skills have names of 8–25 characters and descriptions of 49–429, about 5,000 characters
together, inside the catalog budget Codex documents (2% of the context window, or 8,000
characters).

One source frontmatter is not valid YAML: the `brain-ingest` description contains an
unquoted `: `. Codex's parser repairs such a line (it quotes a scalar that holds `: `), and
Claude Code reads it, but the copies should not lean on a repair heuristic. Task 1.1
quotes that description in the source, and the check (D1) parses every frontmatter as
YAML and checks `name` and `description` against Codex's limits.

Claude Code tool names in skill text (`AskUserQuestion`, `Task`) stay. A Codex agent asks
in the chat where a skill says to use `AskUserQuestion`. The `brain-research*` skills,
which fan out to parallel agents, are best effort in Codex, as they already are in tools
without web search.

### D5. The session hook runs the Claude Code hook script, by a relative path

What Codex offers (docs, [hooks](https://learn.chatgpt.com/docs/hooks), and source):

- `<repo>/.codex/hooks.json` with the same JSON shape as Claude Code's `hooks` block. Hooks
  are on by default; the old `codex_hooks` feature flag is an alias that is no longer
  needed.
- The command runs in the session's folder. There is no project-folder variable like
  `$CLAUDE_PROJECT_DIR`; stdin carries JSON with `cwd`.
- On Windows the command runs in PowerShell (`pwsh`, else Windows PowerShell), and falls
  back to `cmd.exe /C`. `commandWindows` can override it.
- Plain stdout of a SessionStart hook becomes context, up to `additionalContextLimit`
  tokens (default 2,500). Above that, Codex writes the output to a temporary file and keeps
  its head and tail.
- A project hook runs only once the user trusts the project **and** approves the hook in
  `/hooks` (Settings → Hooks in the app). The approval is stored per absolute path of
  `hooks.json`, so every clone approves once. A change to the command string asks again;
  a change to the script does not.

**Decision.** `.codex/hooks.json` holds one SessionStart hook (matcher
`startup|resume|clear|compact`) whose command is
`python .claude/hooks/load_vault_map.py`:

- **No absolute path, no second script.** It runs the file Claude Code runs. The script
  takes `$CLAUDE_PROJECT_DIR` when set and the current folder otherwise, which in Codex
  is the base root, so it needs no change.
- **Shell-agnostic.** A relative path is the one form that bash, PowerShell, Windows
  PowerShell and cmd all read the same way, so no `commandWindows` is needed. `python` is
  the interpreter `.claude/settings.json` already uses.
- **Works without git.** It needs no git, so it works in a base from "Download ZIP".
- **Stable.** The command never needs to change, so owners approve it once per clone.

Its limit: it works only when Codex is started in the base root. Started in a
subfolder, the hook fails, which Codex reports without blocking the session, and
`AGENTS.md` still tells the agent to read the vault map first. Every skill already runs
its scripts from the base root, so this is the same rule as before. `ENVIRONMENTS.md`
says: open the base's root folder in Codex, trust it, approve the hook in `/hooks`.

*Alternatives considered.*

- The pattern in Codex's docs,
  `python "$(git rev-parse --show-toplevel)/.claude/hooks/load_vault_map.py"`, works from
  a subfolder. But it needs git, breaks under the `cmd.exe` fallback, and fails in a ZIP
  base.
- What `/import` writes: an absolute path, the very defect of the migration output.
- A copy of the script in `.codex/hooks/`: a second copy to keep equal, for no gain.

### D6. No wrappers for the slash commands

`.claude/commands/b/*.md` are one-line pointers: "Use the `brain-qa` skill …". A wrapper
skill per command doubles the skill list Codex shows and adds nothing. In Codex the user
starts a skill by name: Codex starts it when the message mentions it as `$brain-ingest`,
or from the `/skills` list; skills do not become `/name` commands. Custom prompts, Codex's
old equivalent of commands, were deprecated in `0.117.0` and removed in `0.118.0`
(2026-03-31), and they were never repository-scoped, so there is nothing else to ship.
`ENVIRONMENTS.md` and the README's "Works beyond Claude Code" section say this, with
`/b:ingest` → `$brain-ingest` as the example.

### D7. The Codex paths are owned files

`.agents/**` and `.codex/**` join the owned class in `.kb-manifest.json`. They ship with
the clone and reach an existing base with `/b:upgrade`, and the owner's edits are kept
like in any owned file. The template-manifest spec already says that class patterns do
not claim a base's own files, so an owner's `.agents/skills/my-skill/` or `.agents/rules/`
(Antigravity) stays theirs.

`dev/check_manifest.py` needs no change: the new tracked files match the owned pattern.
`known-hashes.json` picks them up at the release, as for any new file.

### D8. What an existing base gets

At the upgrade to the release with this change, the plan adds about 25 files under
`.agents/skills/` and `.codex/`. Nothing under `content/`, no rendered file. For an owner
who uses only Claude Code nothing changes.

An owner who edits a skill in `.claude/skills/` and also uses Codex has two copies to keep
in step, without the generator (it lives in `dev/`, which never ships). The changelog
entry and `ENVIRONMENTS.md` say so: copy the edited `SKILL.md` to `.agents/skills/` by
hand. See Open questions.

A base where the owner already ran Codex's migration has untracked files at the same
paths. Codex's `/import` (Settings → Import in the app) copies `.claude/skills/` to
`.agents/skills/` and skips any target that already exists. It turns `.claude/commands/`
into `source-command-*` skills, rewrites "Claude" and `CLAUDE.md` in each `SKILL.md`, and
writes `.codex/hooks.json` with absolute paths when that file is missing. Once the
template ships `.agents/skills/` and `.codex/hooks.json`, a later `/import` leaves them
alone. It still adds the wrapper skills, so the docs advise against running it in a base.
An owner who ran it before upgrading has local files at the template's new paths; task 6.2
checks what the plan does with such a file before the release.

### D9. The migration output is deleted first

The untracked `.agents/` and `.codex/` in the maintainer's checkout go before the
implementation starts (task 0.1), all of it: none of it is reused, the generator writes
the copies anew. The check from D1 fails on any file under `.agents/skills/` it did not
write, so leaving them would fail every local test run in that checkout, which is the
point: an accidental `git add -A` of migration output can no longer pass the tests.
They were never committed, so there is nothing to revert and nothing in any base.

## Risks / Trade-offs

- **[Two copies of each `SKILL.md` in every base]** → About 25 small text files. The check
  keeps them equal in the template. The alternative, symlinks, breaks on Windows and in
  ZIP downloads.
- **[Owners who edit a skill and use Codex get drift]** → Said in the changelog and
  `ENVIRONMENTS.md`. Shipping the generator would fix it; it is an open question.
- **[Codex's skill or hook format changes]** → The copies are plain Agent Skills files,
  the hook is one JSON entry; a format change means a new generator rule, in one place.
  Codex moves fast: custom prompts went from deprecated to removed in five days,
  the docs moved domain, the hooks flag was renamed. The design leans only on documented
  parts (`.agents/skills/`, `.codex/hooks.json`, plain stdout), and task 3.3 records the
  Codex version it was tried with.
- **[The hook needs two approvals per clone (project trust, then `/hooks`)]** → Without
  them only the hook is missing. Skills still load (per the source; the docs don't say),
  and `AGENTS.md` still points at the vault map. `ENVIRONMENTS.md` names both steps.
- **[A grown base's vault map exceeds Codex's default hook output limit]** → See Open
  questions; until then Codex keeps the head and tail and saves the rest to a file.
- **[Contributor forgets to run the generator]** → CI fails and names the copy; the fix
  is one command.
- **[Skills say "Claude"]** → A few lines say "Claude Code" where the agent could be Codex.
  Harmless for the task; left as is to keep D4 simple.

## Migration Plan

1. Implement on a branch, release in a minor version (`0.4.0` or with `0.3.x` if Paweł
   prefers, nothing breaking).
2. After the release, `/b:upgrade` brings the copies to existing bases; the
   `second-brain-demo-recipes` upgrade checks it on a real base.
3. Rollback: revert the commit in the template; a base reverts its upgrade commit.

## Open Questions

- **Ship the generator to bases?** As a script in `brain-upgrade`, an owner could
  regenerate after editing a skill. Paweł decided `dev/` for now (2026-11-09). Worth
  revisiting if course participants on Codex edit skills.
- **Version.** Ship in `0.3.x` or wait for `0.4.0`? Nothing depends on it.
- **Vault map size in Codex.** The hook prints the whole `vault-map.md`. In the
  maintainer's base it is 22 KB, several times Codex's default limit of 2,500 tokens.
  `additionalContextLimit` in `.codex/hooks.json` can raise it (the source shows no upper
  bound). Raise it, and to what, or leave the default and the spill? Claude Code caps hook
  output too, so the size of the map may deserve its own task.
- **Start from a subfolder.** Is the base-root rule of D5 acceptable, or should the hook
  use the git-root form and give up ZIP bases and the `cmd.exe` fallback?
