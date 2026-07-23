# Environments — where this template runs

You do **not** need Claude Code, a terminal, or git commands to use this template.
It is plain markdown files plus instructions an agent reads. Any tool where an AI
assistant can reach your files can drive it.

> Verified 2026-07-08 against official docs (Anthropic, GitHub, OpenAI, Google,
> Cursor). The one hard requirement: **the agent has access to your files / repo.**

## Tool matrix

| Environment | File access | `.claude/commands` | Git without commands | Reads instructions from |
|---|---|---|---|---|
| **Claude Code** (CLI) | native local | **native** `/slash` | conversation | `CLAUDE.md` + `.claude/` |
| **Claude Desktop → Code tab** | native local (Claude Code in a GUI) | **native** `/slash` | visual diff + commit/PR + conversation | `CLAUDE.md` + `.claude/`; `AGENTS.md` via `@AGENTS.md` |
| **Claude Desktop → Chat / Cowork** | Cowork native; Chat via Filesystem MCP | not native → conversation | conversation (Cowork) | `CLAUDE.md`; commands not guaranteed |
| **GitHub Copilot** (VS Code / cloud / app) | edits locally; cloud agent on a clone | not native → conversation; cloud: assign an Issue → PR itself; native via `.claude/skills` or `.github/prompts` | Source Control UI (buttons + AI-commit) / cloud agent opens the PR | `AGENTS.md` + `CLAUDE.md` + `.claude/rules` + `.claude/skills` |
| **Codex** (IDE ext / cloud / app) | edits locally (IDE/app) or in the cloud | not native → conversation; native via `.agents/skills` | app/cloud: push modal + PR, no terminal; conversation | `AGENTS.md` (`CLAUDE.md` via `project_doc_fallback_filenames`) |
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

## The honest limit

The only setup that will **not** work is a plain chat app with **no access to your
files**. Either pick one of the tools above, or connect a folder to it via an MCP
filesystem connector — but that is more technical and unnecessary to start.

---

_Sources: code.claude.com/docs (desktop, `.claude` directory, memory),
code.visualstudio.com/docs (agent customization: custom instructions, agent skills,
prompt files), docs.github.com/copilot (cloud agent), developers.openai.com/codex
(skills, AGENTS.md, config reference), Google Antigravity codelabs, cursor.com/docs
(rules, commands, git). Verified 2026-07-08._
