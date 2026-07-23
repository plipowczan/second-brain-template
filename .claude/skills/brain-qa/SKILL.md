---
name: brain-qa
description: Use when user says "research X", "what do my notes say about X", "co mam w notatkach o X". Synthesizes an answer from the vault citing wikilinks; offers to save substantial answers to `_outputs/answers/`.
---

# Q&A

## When to use

Trigger phrases: "research X", "what do my notes say about X", "co mam w notatkach o X". The user wants an answer drawn from existing vault content.

## Workflow

1. Read `content/_indexes/vault-map.md` → identify relevant folders and tags for the question.
2. Read matching sections of `content/_indexes/catalog.md` → identify candidate notes. Note each candidate's repo-root-relative file path (`content/<TOPIC>/.../<Note>.md`) from its catalog folder section — you'll need it for citations.
3. Read `content/_indexes/graph.md` for link chains starting from candidates.
4. Read the actual note files — only the ones identified, not the whole vault.
5. Synthesize the answer. **Cite every vault-drawn claim as a markdown link**, not a wikilink: `[Note Title](<percent-encoded repo-root path>)`. Rules:
   - **Label** = the plain note title, readable, spaces and parens left as-is.
   - **URL** = the repo-root-relative path from step 2, **percent-encoded**: space → `%20`, `(` → `%28`, `)` → `%29`. An unencoded space or `)` breaks the link.
   - Example: `[Open Knowledge Format (OKF)](content/AI/KNOWLEDGE/INFO/Open%20Knowledge%20Format%20%28OKF%29.md)`
   - Do **NOT** use wikilink `[[ ]]` syntax and do **NOT** wrap the URL in quotes.
   - This renders as a clean clickable label that opens the file in **Claude Desktop** and **VSC markdown preview**. Note: the **VS Code integrated terminal cannot make spaced file paths clickable** (upstream VS Code OSC-8 bug) — citations won't be clickable there regardless of format; this is a known external limitation, not a citation error.

   Clearly distinguish wiki content from inference. Flag gaps where the vault has no coverage.
6. If the answer is substantial, offer the user three follow-ups:
   - Save to `content/_outputs/answers/YYYY-MM-DD_<topic>.md` (type `answer-note`). **Inside the saved vault note, cite with `[[wikilinks]]`, not markdown links** — wikilinks are the vault convention, render in Obsidian, and feed `graph.md`. The markdown-link form is for the chat answer only.
   - Promote to a full wiki article via the `brain-compile` skill.
   - File the new content back into existing notes via the `brain-enhance` skill.

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
