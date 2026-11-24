# Proposal

## Why

A measurement of `/b:qa` on a real base (40 questions, PL-829, PL-830) found full
accuracy and a cost made by the fixed part of the protocol, not by the search. On every
question the agent read `vault-map.md` and `LIMITS.md` whole, and a separate model call
only loaded the skill. The protocol also said one thing and the agent did another: the
skill said to read the matching sections of `catalog.md`, and in 50 runs out of 50 the
agent searched the catalog with a pattern instead and never read a section or `graph.md`.

PL-833 rewrote the protocol to match what works and measured it on a copy of that base
with the same 40 questions. Accuracy held (34/34 answered, 6/6 correct "the vault does not
cover this"). Text read from the vault fell by 63 %, processed input by 18 to 23 % from the
protocol and by a further 8 to 14 % with the command change, and the cost of the 40
questions went from 8.91 to 6.75 USD. Paweł accepted the change on 2026-11-24.

## What Changes

- **brain-qa searches the catalog with a pattern first.** Step 1 searches `catalog.md`
  case-insensitively for the question's key terms, in the vault's language and the
  question's, and reads only the matching lines. The map, the folder sections of the
  catalog and a direct search of the notes become a fallback for when the patterns find
  nothing, and the skill says the vault does not cover a question only after all three
  found nothing.
- **`graph.md` is searched by title, never read whole**, and only when the question needs
  links.
- **`LIMITS.md` is read only before a claim of certainty.** Three of its rules now sit in
  the skill and apply to every answer (one note citing one source is that source's view;
  two notes that agree may rest on the same source; an unread note is a gap, not
  support). The file is read before the answer says the vault is sure, complete or
  consistent, or when the user asks how far to trust it. This stays within the
  `method-limits` requirement of `add-quality-guards`.
- **`/b:qa` includes the skill text.** The command file pulls in
  `.claude/skills/brain-qa/SKILL.md` by file reference and tells the agent not to load
  the skill again, which removes one model call. The skill text stays in one file. A
  question asked without the command, and Codex, which has no commands, load the skill
  as before.
- **`AGENTS.template.md` Navigation Protocol follows the same rules.** The map is read
  first only for an operation that writes or reorganizes notes, unless it is already in
  context; a question starts from the catalog; the catalog and the graph are searched
  with a pattern; `content/` is searched directly only after the catalog found nothing.

Not in this change: trimming the vault map that the session-start hook prints (it feeds
every workflow and needs its own measurement on an instance that has the hook), and the
rest of the session start.

## Capabilities

### New Capabilities

- `qa-navigation`: how brain-qa and the agent instructions find the notes for a question
  (catalog pattern first, fallback order, graph search, when `LIMITS.md` is read) and how
  the `/b:qa` command carries the skill.

### Modified Capabilities

None. The `method-limits` requirement on reading `LIMITS.md` lives in the unarchived
`add-quality-guards` change, not in `openspec/specs/`, so there is no spec to modify. The
new requirements are written to stay compatible with it.

## Impact

- `.claude/skills/brain-qa/SKILL.md` (workflow steps 1 to 7; frontmatter unchanged, so
  the Codex stub does not change).
- `.claude/commands/b/qa.md`.
- `AGENTS.template.md` (Navigation Protocol).
- `CHANGELOG.md` (`[Unreleased]`, `Changed`).
- Existing bases get the skill and the command with `/b:upgrade`. An untouched
  `AGENTS.md` is re-rendered by the upgrade; an edited one gets the difference as a
  proposal.
- `LIMITS.md` and the session-start hook do not change.
