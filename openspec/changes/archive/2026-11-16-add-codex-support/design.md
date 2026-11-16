# Design

## Context

Claude Code reads skills from `.claude/skills/<name>/SKILL.md`, slash commands from
`.claude/commands/`, and its session hook from `.claude/settings.json`, which runs
`python "$CLAUDE_PROJECT_DIR/.claude/hooks/load_vault_map.py"`. The hook prints the vault
map (`content/_indexes/vault-map.md`, the index of the base's notes) into the session.
Codex reads `AGENTS.md` and looks for skills and hooks elsewhere (D2, D5). Today the
template ships only one file for Codex: `AGENTS.template.md`, which onboarding renders into
`AGENTS.md`.

The migration output (see the proposal's Why), checked on 2026-11-09 in the maintainer's
checkout of this repository. That checkout is not the maintainer's own base, which is the
separate `brain` repository.

| Path | Content | State |
|------|---------|-------|
| `.agents/skills/brain-*`, `excalidraw-diagram` | 20 copies of the skills, scripts and tests included | Every `.claude` became `.Codex` and every `CLAUDE` became `AGENTS` or `Codex`: script paths that exist nowhere, `brain-onboard` renders `AGENTS.md` twice and looks for `Codex.template.md`. Stale since PR #14: `brain-upgrade` still says `plan --source`, two test files missing. |
| `.agents/skills/source-command-b-*` | 19 skills of one line each: "Use the `brain-qa` skill …" | Wrappers of `.claude/commands/b/*.md`, which are already one-line pointers to a skill. |
| `.codex/hooks.json` | SessionStart runs `python '<absolute path of the checkout>\.codex\hooks\load_vault_map.py'` | Absolute path: works in this one folder only. Otherwise the same shape as `.claude/settings.json`, with no matcher. |
| `.codex/hooks/load_vault_map.py` | Byte-identical to `.claude/hooks/load_vault_map.py` | A second copy of the same script. |
| `.codex/agents/web-search-agent.toml` | `.claude/agents/web-search-agent.md` converted | Points at `.Codex/agents/web-search-modules/`. |

Facts about the skills that shape the design, checked on `main` at `08fa2c1` on
2026-11-16:

- There are 21 skills; `brain-watch` is the newest. Every command in a `SKILL.md` calls
  its script by the repository-root path
  (`python .claude/skills/brain-lint/scripts/lint_scan.py`). Those paths exist in every
  base.
- Some prose names a file relative to the skill's folder (`scripts/bundle.py` in
  `brain-export`, `references/color-palette.md` in `excalidraw-diagram`). Claude Code
  reads such a path against the skill's folder, which it gives the agent as the skill's
  base directory.
- Several lines mention `CLAUDE.md`. In a base, `CLAUDE.md` exists and points to
  `AGENTS.md`, so the mentions hold for Codex too. In `brain-onboard` and `brain-upgrade`,
  `CLAUDE.md` means the file itself, which must be rendered.
- Every skill has `name` and `description` in its frontmatter; the five `brain-research*`
  skills also have `allowed-tools` and `user-invocable`. Parsed with PyYAML, two
  frontmatters are broken (D4).
- Skill text names the `/b:*` commands, and `AGENTS.template.md` lists the workflows by
  command only.

## Goals / Non-Goals

**Goals:**

- An owner who works in Codex gets every template skill and reads the same skill text as
  in Claude Code.
- One place to edit a skill. A stale Codex file fails CI before it can ship.
- The session hook works in the root of every clone, wherever the clone lives.
- The migration output in the maintainer's checkout is replaced, not shipped.

**Non-Goals:**

- Codex agents converted from `.claude/agents/`.
- Native files for Copilot, Cursor, Antigravity.
- Regenerating Codex files inside a base.
- Rewriting skills for Codex's tool names.

## Decisions

### D1. The Codex files are generated, by an author tool in `dev/`

`dev/build_codex_files.py` (the generator) writes the stubs under `.agents/skills/` (D3)
and `.codex/hooks.json` (D5). Like `dev/build_known_hashes.py`, it has a `--check` mode
(the check) that writes nothing and exits non-zero with the paths that differ. It is
built on the same `kbtemplate` module as `dev/check_manifest.py`: the manifest decides
which skills ship, and files are compared the way the stamp hashes compare them
(`kbtemplate.content_hash`, which ignores line endings). It parses frontmatter with
PyYAML, which `requirements.txt` already lists and CI installs. `dev/` never ships, so no
base needs the generator or PyYAML for it.

`tests/run_tests.py` runs the check where `dev/` exists, next to `dev/check_manifest.py`,
so the `Tests` workflow runs it on Linux and Windows for every pull request.

The check fails when:

- a stub or `.codex/hooks.json` differs from what the generator would write, or is
  missing;
- `.agents/skills/` holds a directory or file with no source skill (this catches the
  `source-command-*` wrappers and any other leftover of the migration);
- a source frontmatter is not valid YAML, lacks a string `name` or `description`, or YAML
  reads less of the description than the file holds (D4).

Write mode fails on the same frontmatter errors and then writes nothing. Otherwise it
writes every stub and the hook, and deletes files under `.agents/skills/` that have no
source, so one run leaves the check passing.

*Alternatives considered.*

- Symlinks from `.agents/skills` to `.claude/skills`: git on Windows checks them out as
  small text files unless symlinks are enabled, and "Download ZIP" drops them, while the
  README promises a base works from a ZIP.
- A config key that points Codex at `.claude/skills/`: none exists (D2).
- A copy step in the release process only: the files would drift between releases and
  no check would report it.

### D2. Where Codex looks: `.agents/skills/` in the repository

Checked on 2026-11-09 against the Codex docs (`developers.openai.com/codex/*` now
redirects to `learn.chatgpt.com/docs/*`) and the `openai/codex` source at `0598a96e`
(latest release `rust-v0.167.0`, 2026-11-06):

- Codex scans `.agents/skills/` in every folder from the project root (found by `.git`)
  down to the session's folder, plus `~/.agents/skills/` and the system locations
  ([build-skills](https://learn.chatgpt.com/docs/build-skills)).
- It does not read `.claude/skills/`, and no `config.toml` key adds a skill folder. Only
  Codex's app-server API, meant for programs that embed Codex, can add another folder.
- A project `.codex/skills/` also works, but only the Codex source shows it, so the
  template uses the documented `.agents/skills/`.
- Repository skills load without the project trust that hooks need (Codex source; the
  Codex docs do not say).

So a file in `.agents/skills/` is the only documented way, short of symlinks (D1).

A base from "Download ZIP" has no `.git`. The design assumes that Codex then treats the
session's folder as the project root, so a session started in the base root finds
`.agents/skills/`. Neither the Codex docs nor the check above settle it. Task 0.3 tried
it on 2026-11-16: a ZIP base lists the stubs and runs the hook, with no `git init`.

### D3. A stub per skill points at the source

For each skill that ships, the generator writes one file, `.agents/skills/<skill>/SKILL.md`
(a stub):

```markdown
---
<the source's frontmatter lines, unchanged>
---

This skill's instructions are in `.claude/skills/<skill>/SKILL.md`. Read that file and
follow it. Its folder, `.claude/skills/<skill>/`, is this skill's base directory.
If that file does not exist, tell the user that this skill was removed from this base,
and stop.
```

The last sentence covers a base that deleted a template skill but still has its stub
(D8). Codex lists the skill and picks it by its frontmatter, as for any skill. When the skill
starts, the agent reads the source file, which is the text Claude Code reads. A relative
path in it resolves against the same folder in both agents. Nothing else is written under
`.agents/skills/<skill>/`.

What this buys:

- **One body per skill.** An owner's edit to a skill reaches both agents. An upgrade shows
  a skill change once, not once per copy.
- **No source edits for Codex.** Scripts, `references/` and relative mentions stay where
  they are; no copy lacks them.
- **Small Codex files.** A stub changes only when its skill's frontmatter changes.

What it costs:

- **One more file read** each time a skill starts in Codex.
- **It relies on the agent following the pointer**, which CI cannot test. Codex's own
  migration relies on the same thing: each of its wrapper skills is one line, "Use the
  `brain-qa` skill …". Task 0.3 tried stubs in real sessions before any code was
  written, and Codex followed each one (`review.md`).
- **The frontmatter is in two places.** An owner who edits a description, or adds a
  skill, writes the stub by hand (D8).

*Alternatives considered.*

- **A full copy of each skill's Markdown** (the first version of this design): the copy
  holds `SKILL.md` and the skill's other `*.md` files, byte for byte, and Codex gets the
  instructions without a second read. But in a base the copies drift. An owner's edit to
  a skill never reaches Codex unless they copy it by hand. An upgrade shows each skill
  change twice, and a hand copy means two conflicts for every later change. The copies
  also lack the skill's scripts and other files, so relative mentions must become
  repository-root paths, and the check needs a rule for them. This is the fallback if
  task 0.3 shows that Codex does not follow a stub; that rule then needs its own design
  and review.
- **A copy of the whole skill folder:** every script twice in every base, two copies an
  owner can edit separately, and `known-hashes.json`, the largest file in the template,
  twice.

### D4. No text is rewritten; two frontmatters are fixed at the source

A stub's frontmatter is the source's, unchanged: no `CLAUDE.md` → `AGENTS.md`, no
`.claude` → anything. The migration shows the cost of a rewrite: one blind replacement
broke onboarding and every script call. The mentions of `CLAUDE.md` are true in a base,
which has both files.

Codex reads `name` and `description` and ignores keys it does not know (`allowed-tools`,
`user-invocable`) without a warning. It needs a non-empty `description` and a `name` of
at most 64 characters, and it shows the model at most 1024 characters of a description.
On `main` the longest name has 25 characters and the longest description 452, so the
check does not test these limits. All descriptions together hold about 5,200 characters,
inside the budget the Codex docs give the skill list (2% of the context window, or 8,000
characters).

Parsed with PyYAML on `main`, two source frontmatters are broken:

- **`brain-export`:** the unquoted description contains `"export #tag"`. In YAML, a space
  before `#` starts a comment, so YAML reads 49 of the description's 452 characters.
  Claude Code's skill list shows the cut text today, and Codex would too.
- **`brain-ingest`:** the description contains `touch: shows`, which is not valid YAML.
  Codex's parser repairs such a line and Claude Code reads it, but the fix should not
  depend on a repair.

Task 2.1 quotes both descriptions. The check then keeps every frontmatter whole: it fails
when YAML reads less of a description than the line holds.

Two descriptions also tell the user to run `/import` and `/export` (`brain-export`,
`brain-import`). In Codex, `/import` is the migration command. Task 2.2 writes
`/b:import` and `/b:export`, the names of the template's own commands.

Claude Code tool names in skill text stay. Where a skill says to use `AskUserQuestion`,
Codex has no such tool, and the agent is expected to ask in the chat. The five
`brain-research*` skills start parallel agents with Claude Code's `Task` tool, which Codex
does not have. Task 6.5 runs one of them in Codex and records what happens. Until then
the template does not promise them in Codex, and `ENVIRONMENTS.md` says so.

### D5. The session hook runs the Claude Code hook script, by a relative path

What Codex offers (Codex docs, [hooks](https://learn.chatgpt.com/docs/hooks), and Codex
source):

- `<repo>/.codex/hooks.json` with the same JSON shape as the `hooks` block of
  `.claude/settings.json`. Hooks are on by default; the old `codex_hooks` feature flag
  still works but is no longer needed.
- The command runs in the session's folder. There is no project-folder variable like
  `$CLAUDE_PROJECT_DIR`; stdin carries JSON with `cwd`.
- On Windows the command runs in PowerShell (`pwsh`, else Windows PowerShell); when
  neither is found, in `cmd.exe /C`. `commandWindows` can override it.
- Plain stdout of a SessionStart hook is added to the model's context, up to
  `additionalContextLimit` tokens (default 2,500). Above that, Codex writes the output to
  a temporary file and keeps its head and tail in context.
- A project hook runs only once the owner trusts the project **and** approves the hook in
  `/hooks` (Settings → Hooks in the app). Codex stores the approval per absolute path of
  `hooks.json`, so the owner approves once per clone. Codex asks again when the command
  string changes, not when the script changes.

**Decision.** The generator writes `.codex/hooks.json` with exactly this content:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/load_vault_map.py"
          }
        ]
      }
    ]
  }
}
```

It has the shape of `.claude/settings.json` and of the file Codex's own migration wrote.
It has no matcher, so it runs at every kind of session start.

- **No absolute path, no second script.** It runs the file Claude Code runs. The script
  takes `$CLAUDE_PROJECT_DIR` when set and the current folder otherwise, which is the base
  root when Codex starts there, so the script needs no change.
- **Shell-agnostic.** A relative path is the one form that bash, PowerShell, Windows
  PowerShell and cmd all read the same way, so no `commandWindows` is needed. `python` is
  the interpreter `.claude/settings.json` already uses.
- **Works without git**, so a base from "Download ZIP" runs it.
- **Stable.** The command does not depend on where the clone lives, so the owner approves
  it once per clone.

Its limit: it works only when Codex starts in the base root. When Codex starts in a
subfolder, the hook fails; Codex reports the failure and the session continues. `AGENTS.md`
still tells the agent to read the vault map first. Every skill already runs its scripts
from the base root, so this is the same rule as before. `ENVIRONMENTS.md` says: open the
base's root folder in Codex, trust it, approve the hook in `/hooks`.

An owner may add hooks of their own to this file. It is an owned file: the upgrade keeps
the owner's edit and asks only if the template changes the file too, which this design
does not plan.

*Alternatives considered.*

- The pattern in the Codex docs,
  `python "$(git rev-parse --show-toplevel)/.claude/hooks/load_vault_map.py"`, works from
  a subfolder. But it needs git, breaks under the `cmd.exe` fallback, and fails in a ZIP
  base.
- What `/import` writes: an absolute path, the defect of the migration output.
- A copy of the script in `.codex/hooks/`: a second copy to keep equal, for no gain.

### D6. No wrappers for the slash commands

`.claude/commands/b/*.md` are one-line pointers: "Use the `brain-qa` skill …". A wrapper
skill per command doubles the skill list Codex shows and adds nothing. A stub (D3) is not
such a wrapper: there is one per skill, under the skill's own name, so the list does not
grow.

In Codex the owner starts a skill by name: Codex starts it when the message mentions it
as `$brain-ingest`, or from the `/skills` list; skills do not become `/name` commands.
Custom prompts, Codex's old equivalent of commands, were deprecated in `0.117.0` and
removed in `0.118.0` (2026-03-31), and they were never repository-scoped, so there is
nothing else to ship.

Skill text keeps naming the `/b:*` commands. `AGENTS.template.md` gets one sentence under
"Workflows": an agent without slash commands treats `/b:<name>` as the `brain-<name>`
skill. `AGENTS.md` reaches the Codex agent in every session. For the owner,
`ENVIRONMENTS.md` and the README's "Works beyond Claude Code" section give `/b:ingest` →
`$brain-ingest` as the example.

### D7. Two narrow owned patterns

`.agents/skills/**` and `.codex/hooks.json` join the owned class in `.kb-manifest.json`.
They ship with the clone and reach an existing base with `/b:upgrade`, and the owner's
edits are kept as in any owned file. The template-manifest spec already says that class
patterns do not claim a base's own files, so an owner's `.agents/skills/my-skill/` stays
theirs.

Any other file under `.agents/` or `.codex/` matches no class, so `dev/check_manifest.py`
fails if it is committed. That covers the migration's `.codex/hooks/` and
`.codex/agents/`, a personal `.codex/config.toml`, and Antigravity's `.agents/rules/`. A
future Codex file the template wants to ship needs one more pattern, and the manifest
check asks for it.

`dev/check_manifest.py` needs no change. `known-hashes.json` picks the new files up at the
release, as for any new file.

*Alternative considered.* `.agents/**` and `.codex/**`, with the check failing on
anything under them that the generator does not write: more code to police paths the
template does not ship, when the manifest check already does it.

### D8. What an existing base gets

At the upgrade to the release with this change, the plan adds one stub per template skill
and `.codex/hooks.json`, and updates the skills whose frontmatter tasks 2.1 and 2.2 fix.
Nothing under `content/` changes, and no rendered file. `AGENTS.md` gets the sentence from
D6 only when the owner re-renders it, which `/b:upgrade` offers only for an untouched
file; the changelog says so.

What an owner does after that:

- **Uses only Claude Code:** nothing. Claude Code does not read the new files. Deleting
  them is harmless but brings back a "restore?" row for each one at every later upgrade,
  so `ENVIRONMENTS.md` says to keep them.
- **Edits a skill's text:** nothing; the stub points at the edited file.
- **Edits a skill's description, or adds a skill:** writes or edits the stub by hand, as
  in D3. `ENVIRONMENTS.md` shows the file.
- **Deleted a template skill:** the upgrade still adds its stub. The planner does not tie
  the stub to its source: the deleted source is a `restore?` row, not selected, and the
  stub is a new template file, selected. The stub then tells Codex the skill is missing
  (D3). To drop it, the owner deletes `.agents/skills/<skill>/` after the upgrade and
  commits; later upgrades list it as `restore?`, not selected. `ENVIRONMENTS.md` says so.

**A base where the owner already ran the migration.** `/import` does five things:

- It copies `.claude/skills/` to `.agents/skills/` and skips any target that already
  exists.
- It turns `.claude/commands/` into `source-command-*` skills.
- It replaces "Claude" and `CLAUDE.md` in each copied `SKILL.md`.
- It writes `.codex/hooks.json` with an absolute path when that file is missing.
- It writes `.codex/hooks/` and `.codex/agents/`, as seen in the maintainer's checkout.

Once the template ships stubs and `hooks.json`, a later `/import` leaves them alone. It
still adds the wrapper skills, so `ENVIRONMENTS.md` advises against running it in a base.

An owner who ran it before upgrading has their own files at the template's new paths. The
upgrade lists each one as a conflict ("new template file, but this base has its own file
here") and does not write over untracked work. Committing the migration output does not
help: the broken copies would then be the owner's own version, which the upgrade keeps or
reports as a conflict. Choosing "keep" on those rows lets the upgrade finish, but the
broken copies stay live in Codex.

So the upgrade has one step before it, in the changelog entry and `ENVIRONMENTS.md`:

- **First:** copy `.agents/` and `.codex/` to a folder outside the base. An owner who
  edited an imported skill or the imported hook carries the edit over to
  `.claude/skills/<skill>/SKILL.md`, `.claude/settings.json`, or a skill of their own.
- **Required:** delete `.agents/skills/<skill>/` for each template skill, and
  `.codex/hooks.json`. They stand at the template's paths and block the upgrade.
- **Advised:** delete every `.agents/skills/source-command-*`, `.codex/hooks/` and
  `.codex/agents/`. They do not block the upgrade, but the wrappers double the skill list
  (D6) and the rest is broken.
- **If the migration output was committed:** delete it with `git rm -r` and commit the
  deletion. `apply` refuses planned paths with uncommitted changes, and a deletion is one.
- The owner's own skills under `.agents/skills/` stay.

Tasks 6.3 and 6.4 test this end to end, with the migration output untracked and with
it committed: after that step the upgrade applies and commits, every stub equals the
template's, and the owner's own skill is untouched.

### D9. The migration output is deleted first

Task 0.1 saves a copy of the migration output outside any repository, for tasks 6.3
and 6.4, and then deletes the untracked `.agents/` and `.codex/` folders in the
maintainer's checkout. Nothing in them is reused; the generator writes new files. Until
they are deleted, the check fails every local test run in that checkout, because
`.agents/skills/` holds files with no source or with other content. That is intended:
migration output cannot pass the tests there. The folders were never committed, so no
release contains them.

## Risks / Trade-offs

- **[Codex does not follow a stub]** → Task 0.3 found that it does (Codex 0.163 and
  0.169). If a later Codex stops following stubs, the generator writes full copies
  instead (D3, fallback), and Paweł is asked again.
- **[The frontmatter is in two places]** → The check keeps the copies equal in the
  template. In a base, an owner who edits a description writes the stub by hand (D8). A
  description changes rarely.
- **[Codex's skill or hook format changes]** → A stub is a plain skill file and the hook
  is one JSON entry, so a format change means a change to the generator, in one place.
  Codex's formats change often: custom prompts were deprecated and removed one release
  apart, the docs moved domain, and the hooks feature flag was replaced. The design leans
  only on documented parts (`.agents/skills/`, `.codex/hooks.json`, plain stdout), and
  task 0.3 records the Codex version it was tried with.
- **[Security: the hook runs code from the base at every session start]** → Codex
  approves the command string, not the script. A later release that changes
  `load_vault_map.py` therefore runs at the next session without a new prompt, as the
  Claude Code hook in `.claude/settings.json` does today. The owner consents to each
  release when they upgrade, and what this repository tags is what runs ("What instances
  trust" in `CONTRIBUTING.md`). Only `.codex/hooks.json` ships under `.codex/` (D7), so no
  other Codex setting reaches a base.
- **[The hook needs two approvals per clone (project trust, then `/hooks`)]** → Without
  them only the hook is missing. Skills still load (per the Codex source; the Codex docs
  do not say), and `AGENTS.md` still points at the vault map. `ENVIRONMENTS.md` names both
  steps.
- **[A large base's vault map exceeds Codex's default hook output limit]** → See Open
  Questions. Until that question is settled, Codex keeps the head and tail of the map and
  writes the output to a file.
- **[The hook prints another project's map, or garbled text]** → The script prefers
  `$CLAUDE_PROJECT_DIR` when it is set, so a Codex session started from a shell that
  inherited it prints that project's map. On Windows the script writes stdout in the
  system code page, which can garble or fail on characters outside it. Both already hold
  for Claude Code; they are a separate issue, not part of this change.
- **[Other tools may read `.agents/skills/` too]** → `ENVIRONMENTS.md` lists Copilot and
  Cursor as reading `.claude/skills/`. Task 0.4 found in their docs that both also read
  `.agents/skills/`. Copilot CLI keeps the stub and hides the source; Cursor's docs do
  not say which of two same-named skills wins. Either way the agent reaches the same
  text, and `ENVIRONMENTS.md` says so.
- **[A contributor forgets to run the generator]** → CI fails and names the file; the fix
  is one command.
- **[Skills say "Claude"]** → A few lines say "Claude Code" where the agent could be
  Codex. The agent can still follow them; D4 leaves the text unchanged.

## Migration Plan

1. Implement on this branch, on top of `main`. Release in `0.4.0` (Open Questions).
2. Existing bases get the stubs and the hook with `/b:upgrade`. A base that ran the
   migration first copies its output aside and deletes the paths listed in D8. The changelog's "Existing bases"
   paragraph says so, together with the rule to edit a stub by hand.
3. The upgrade of the demo base `second-brain-demo-recipes` checks it on a real base.
4. Rollback: tags never move, so a defect gets a new patch release. A base reverts its
   upgrade commit or upgrades to that release.

## Open Questions

Paweł answered all of them on 2026-11-16, each as the EGM review recommended.

- **Stub or full copy?** (D3, added by the EGM review.) *Decided:* a stub per skill. The
  full copy stays the fallback if task 0.3 shows that Codex does not follow a stub, and
  Paweł is asked before it is taken.
- **Ship the generator to bases?** If it shipped as a script in `brain-upgrade`, an owner
  could regenerate the Codex files after editing a skill. With stubs, a base needs it
  only when an owner adds a skill or edits a description, and a stub is a short file.
  *Decided:* the generator stays in `dev/` (first on 2026-11-09, confirmed). Worth
  revisiting if owners who use Codex edit skills often.
- **Version.** `0.3.0` was tagged on 2026-11-13, so the choice was `0.3.1` or `0.4.0`.
  This change adds a feature, and `CONTRIBUTING.md` keeps patch releases for defects.
  *Decided:* `0.4.0`.
- **Vault map size in Codex.** The hook prints the whole `vault-map.md`. In the
  maintainer's own base (the `brain` repository) it is 22 KB, roughly 5,500 to 7,500
  tokens, two to three times Codex's default limit of 2,500 tokens.
  `additionalContextLimit` in `.codex/hooks.json` can raise the limit. A new base's map is
  small, Codex keeps the head and tail of a long one, and `AGENTS.md` tells the agent to
  read the map file anyway. *Decided:* leave the default, with no key in the file. The
  size of the map, which Claude Code caps too, gets its own task outside this change.
- **Start from a subfolder.** The base-root rule of D5, or the git-root form, which gives
  up ZIP bases and the `cmd.exe` fallback? *Decided:* the base-root rule. Task 0.3 checks
  that a session started in `content/` still starts.
