# Environments — where this template runs

You do **not** need Claude Code, a terminal, or git commands to use this template.
It is plain markdown files plus instructions an agent reads. Any tool where an AI
assistant can reach your files can drive it.

> Verified 2026-07-08 against official docs (Anthropic, GitHub, OpenAI, Google,
> Cursor); the Codex parts again on 2026-11-16, against the Codex docs and in Codex
> 0.169. The one hard requirement: **the agent has access to your files / repo.**

## Tool matrix

| Environment | File access | `.claude/commands` | Git without commands | Reads instructions from |
|---|---|---|---|---|
| **Claude Code** (CLI) | native local | **native** `/slash` | conversation | `CLAUDE.md` + `.claude/` |
| **Claude Desktop → Code tab** | native local (Claude Code in a GUI) | **native** `/slash` | visual diff + commit/PR + conversation | `CLAUDE.md` + `.claude/`; `AGENTS.md` via `@AGENTS.md` |
| **Claude Desktop → Chat / Cowork** | Cowork native; Chat via Filesystem MCP | not native → conversation | conversation (Cowork) | `CLAUDE.md`; commands not guaranteed |
| **GitHub Copilot** (VS Code / cloud / app) | edits locally; cloud agent on a clone | not native → conversation; cloud: assign an Issue → PR itself; native via `.claude/skills` or `.github/prompts` | Source Control UI (buttons + AI-commit) / cloud agent opens the PR | `AGENTS.md` + `CLAUDE.md` + `.claude/rules` + `.claude/skills` |
| **Codex** (IDE ext / cloud / app) | edits locally (IDE/app) or in the cloud | not native → conversation; native via `.agents/skills`, which the template ships ([Codex](#codex)) | app/cloud: push modal + PR, no terminal; conversation | `AGENTS.md` (`CLAUDE.md` via `project_doc_fallback_filenames`) |
| **Cursor** (IDE) | agent edits locally | native in `.cursor/commands`; `.claude/commands` → conversation/copy; `.claude/skills` recognized (legacy) | Source Control UI + AI-commit + conversation | `AGENTS.md` + `.cursor/rules` (`.cursorrules` legacy) |
| **Antigravity** (IDE) | agent edits locally | reads `.claude/*.md` as instructions; native = `.agents/workflows` | Source Control UI (VS Code fork) + agent | `AGENTS.md` + `.agents/rules` / `~/.gemini/GEMINI.md` |
| **Chat app without file access** | none (unless MCP / connector) | — | — | — |

## Three ways to do git without typing `git ...`

1. **Talk to the agent** — say "save my changes," and it commits for you.
2. **Source Control buttons** — VS Code–based tools (Copilot, Cursor, Antigravity)
   ship a panel with commit/push buttons and AI-generated commit messages.
3. **Cloud mode** — the agent prepares the change and opens a pull request itself.

## Key cross-tool facts

- `.claude/commands/*.md` are **native** slash commands only in Claude Code and
  Claude Desktop (Code). Everywhere else they still work **through conversation** —
  they are ordinary instruction files ("follow the instructions in
  `.claude/commands/b/ingest.md`").
- `AGENTS.md` is the cross-tool instruction file (Codex, Copilot, Cursor, and
  Antigravity read it natively). Claude reads `CLAUDE.md`, wired to `AGENTS.md`
  by the `@AGENTS.md` import line — one source of truth.
- `.claude/skills/<name>/SKILL.md` is recognized as a native `/slash` in Claude
  Code / Desktop, Copilot, and Cursor. This is the basis for an optional future
  migration of the command files (not done — see the template's issue tracker).

## Codex

Codex reads `AGENTS.md`, but not `.claude/skills/` or `.claude/settings.json`. The
template ships two things for it, and both lead back to the files Claude Code uses:

- **Skills.** Each skill has a stub at `.agents/skills/<skill>/SKILL.md`, where Codex
  looks. The stub holds the skill's name and description and tells the agent to read and
  follow `.claude/skills/<skill>/SKILL.md`. Each skill has one text, for both agents.
- **The session hook.** `.codex/hooks.json` runs `python .claude/hooks/load_vault_map.py`,
  the script Claude Code runs, which puts the vault map into the session.

**Start a skill by name.** Codex has no `/b:*` commands. Mention the skill in your
message, `$brain-ingest` for `/b:ingest` (the skill is `brain-` plus the command's name),
or pick it from `/skills`. An `AGENTS.md` rendered from release 0.4.0 or later also tells
the agent that `/b:<name>` means the `brain-<name>` skill.

**Set up each clone once:**

1. Open the base's root folder in Codex, the folder that holds `AGENTS.md`. The hook runs
   only there: in a subfolder such as `content/`, Codex reports the hook as failed and the
   session starts without the vault map.
2. Trust the project when Codex asks.
3. Approve the hook. Codex asks you to review new hooks; you can also open `/hooks` (in
   the app, Settings → Hooks). Pick **Review hooks**, not **Trust all**, and trust only
   `python .claude/hooks/load_vault_map.py`: with plugins installed, the list holds their
   hooks too. If the review fails (Codex 0.169 once reported `config/read failed in
   TUI`), restart Codex or run `/hooks` in the session.

A base downloaded as a ZIP needs nothing extra. Without `.git`, Codex treats the folder
you open as the project and finds the stubs and the hook there (tried with Codex 0.169).

**Other tools.** GitHub Copilot CLI and Cursor read `.agents/skills/` as well as
`.claude/skills/`, so they may list the stub in place of the skill. The stub points them
at the same text.

**The `brain-research*` skills** were written for Claude Code's background agents and its
question form. In Codex 0.169, `$brain-research` ran to the end: Codex asked the skill's
questions in its own question form, and where the skill starts a background web-search
agent, Codex started one of its own subagents, which searched the web and reported back.
Codex does not read the agent definition in `.claude/agents/`, so that subagent follows
only the prompt the skill gives it. The other four (`brain-research-deep`,
`brain-research-add-fields`, `brain-research-add-items`, `brain-research-report`) were not
tried in Codex: check what they write before you rely on it.

**Approve git writes when asked.** Codex's sandbox keeps commands from writing to `.git`
without your approval, so a skill that switches branches or commits, such as
`$brain-onboard`, stops there and asks.

**Do not run `/import` in a base.** Codex's `/import` (Settings → Import in the app)
converts a Claude Code project. It copies the skills into `.agents/skills/` with "Claude"
replaced, which breaks every script path, adds a wrapper skill for each `/b:*` command,
and writes `.codex/hooks.json` with an absolute path. The template already ships what
Codex needs.

**If your base already ran it**, clean up before you run `/b:upgrade` to the release that
adds the stubs (0.4.0):

1. Copy `.agents/` and `.codex/` to a folder outside the base. If you edited an imported
   skill or the imported hook, carry the edit over to `.claude/skills/<skill>/SKILL.md`,
   `.claude/settings.json`, or a skill of your own.
2. Delete `.agents/skills/<skill>/` for each template skill, and `.codex/hooks.json`.
   Required: they stand at the template's new paths and block the upgrade.
3. Delete every `.agents/skills/source-command-*`, `.codex/hooks/` and `.codex/agents/`.
   Advised: the wrappers double the skill list, and the rest is broken.
4. If you had committed that output, delete it with `git rm -r` and commit the deletion.
   The upgrade refuses paths with uncommitted changes, and a deletion is one.

Keep your own skills under `.agents/skills/`: the upgrade leaves them alone.

**After you add a skill or edit a description,** write or edit its stub by hand: the
template's generator does not ship to bases. A stub is this file, with the skill's
frontmatter lines copied unchanged:

```markdown
---
name: my-skill
description: Use when the user says "…". What the skill does.
---

This skill's instructions are in `.claude/skills/my-skill/SKILL.md`. Read that file and
follow it. Its folder, `.claude/skills/my-skill/`, is this skill's base directory.
If that file does not exist, tell the user that this skill was removed from this base,
and stop.
```

An edit to a skill's body needs nothing: the stub points at the edited file.

**After you delete a template skill,** the next `/b:upgrade` still adds its stub, which
tells Codex that the skill was removed. Delete `.agents/skills/<skill>/` after that
upgrade and commit; later upgrades show it as a `restore?` row, not selected.

**Keep `.agents/` and `.codex/` even if you never use Codex.** Claude Code does not read
them, and deleting them brings back a `restore?` row for each file at every upgrade.

## Updating the template without a terminal

`/b:upgrade` is a set of Python commands the agent runs for you, so it works wherever
the agent can run Python on your files. Ask in a sentence where `/slash` commands are not
native: *"follow `.claude/skills/brain-upgrade/SKILL.md`"*. It needs neither git nor a
clone of the template: it downloads the release archive itself, or takes a release
`.zip` you saved (offline). With git it ends in one commit you can review in the Source
Control panel; without git it keeps a copy of every file it replaces in
`.kb-upgrade-backup/`.

## The honest limit

The only setup that will **not** work is a plain chat app with **no access to your
files**. Either pick one of the tools above, or connect a folder to it via an MCP
filesystem connector — but that is more technical and unnecessary to start.

---

_Sources: code.claude.com/docs (desktop, `.claude` directory, memory),
code.visualstudio.com/docs (agent customization: custom instructions, agent skills,
prompt files), docs.github.com/copilot (cloud agent, Copilot CLI skill locations),
learn.chatgpt.com/docs (Codex: skills, hooks, AGENTS.md, config reference; formerly
developers.openai.com/codex), Google Antigravity codelabs, cursor.com/docs (rules,
commands, git, skills). Verified 2026-07-08; Codex 2026-11-16._
