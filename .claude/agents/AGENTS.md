# AGENTS.md — .claude/agents/

## Purpose

Custom **sub-agents** the workflow skills dispatch via the `Task` tool. Each agent is a
markdown file with YAML frontmatter (`name`, `description`, optional `model`) + a system
prompt body. Claude Code auto-discovers `.claude/agents/*.md` (project-scoped).

## Contents

| Agent | Used by | What it does |
|-------|---------|--------------|
| `web-search-agent.md` | `research-deep` (and `research`/`research-add-*` web-supplement steps) | Elite internet-research sub-agent: generates 5–10 query variants, routes to source-specific strategy modules, compiles cited findings. `model: opus`. |
| `web-search-modules/` | loaded by `web-search-agent` | 5 scenario strategy modules the agent `Read`s before searching: `general-web`, `github-debug`, `stackoverflow`, `academic-papers`, `chinese-tech`. |

## Provenance

`web-search-agent` + `web-search-modules/` are vendored from
[Weizhena/Deep-Research-skills](https://github.com/Weizhena/Deep-Research-skills) (MIT),
the upstream of the `research*` skills. See the vault note `AI/TOOLS/Deep-Research-skills`.

## Rules

- **Project-relative paths only.** Upstream assumed a global `~/.claude` install. Here the
  agent loads its modules from `.claude/agents/web-search-modules/` (NOT `~/.claude/…`) so
  the repo — and any kb-template clone — is self-contained. Keep it that way if you re-sync
  from upstream.
- Mirror any change to `kb-template/.claude/agents/` (the drift script only checks
  `.claude/skills/`, so agents must be kept in sync by hand) and log it in
  `kb-template/CHANGELOG.md`.

## Verify

Trigger `/b:research-deep` on a small outline; confirm the sub-agent Reads a module from
`.claude/agents/web-search-modules/` before its first `WebSearch`.
