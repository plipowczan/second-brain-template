---
name: brain-qa
description: Use when user says "research X", "what do my notes say about X", "co mam w notatkach o X". Synthesizes an answer from the vault citing notes, shows both sides of marked contradictions, and saves substantive answers to `_outputs/answers/` with what they rest on and what the vault could not answer. `--no-save` answers without writing.
---

# Q&A

## When to use

Trigger phrases: "research X", "what do my notes say about X", "co mam w notatkach o X". The user wants an answer drawn from existing vault content.

Substantive answers are saved by default, because a good answer — and the part of the question the vault could not answer — is lost when the session ends. Pass `--no-save`, or ask not to save, to answer without writing anything.

## Workflow

1. **Search the catalog with a pattern.** Search `content/_indexes/catalog.md` case-insensitively for the question's key terms and read the matching lines. Do not read the catalog or its sections whole at this step. Build the pattern in the vault's primary language and in the question's language, with synonyms and the words a note title would use: for "przepis na ciasto", search `cake|baking|recipe`. Each matching line is one note: title, type, date, tags, one-line summary, outgoing links. If the first pattern finds nothing useful, try a broader one. Note each candidate's repo-root-relative file path (`content/<TOPIC>/.../<Note>.md`), found by its title (for example a file search for `content/**/<Title>.md`) — you'll need it for citations.
2. **Only when the patterns find nothing:** read the folder table in `content/_indexes/vault-map.md` (skip the read if the map is already in your context), read the matching folder sections of `catalog.md`, then search the notes under `content/` directly. Say that the vault does not cover the question only after all three found nothing. If a catalog section was too large to read in full, remember which parts you skipped: they go into the answer's gaps.
3. **Links, only when the question needs them** — how notes connect, or a candidate that rests on another note: search `content/_indexes/graph.md` for the candidate's title and follow the chain. Do not read `graph.md` whole.
4. Read the actual note files — only the ones identified, not the whole vault.
5. **Contradictions.** If a note you use carries a `> [!contradiction]` callout that bears on the question, present both claims with their sources. Do not pick one without saying so. Each contradiction the answer cannot resolve is a gap (step 9).
6. **Limits.** In every answer, a claim from one note that cites one source is that source's view, two notes that agree may rest on the same source, and a relevant note you did not read is a gap, not support. **Read `LIMITS.md`** (repository root) **only before you say the vault is sure, complete or consistent about something**, or when the user asks how far to trust the answer; then name the limits that apply. If it is missing then, say so and make no claim of certainty.
7. Synthesize the answer. **Cite every vault-drawn claim as a markdown link**, not a wikilink: `[Note Title](<percent-encoded repo-root path>)`. Rules:
   - **Label** = the plain note title, readable, spaces and parens left as-is.
   - **URL** = the repo-root-relative path from step 1, **percent-encoded**: space → `%20`, `(` → `%28`, `)` → `%29`. An unencoded space or `)` breaks the link.
   - Example: `[Open Knowledge Format (OKF)](content/AI/KNOWLEDGE/INFO/Open%20Knowledge%20Format%20%28OKF%29.md)`
   - Do **NOT** use wikilink `[[ ]]` syntax and do **NOT** wrap the URL in quotes.
   - This renders as a clean clickable label that opens the file in **Claude Desktop** and **VSC markdown preview**. Note: the **VS Code integrated terminal cannot make spaced file paths clickable** (upstream VS Code OSC-8 bug) — citations won't be clickable there regardless of format; this is a known external limitation, not a citation error.

   Clearly distinguish wiki content from inference. Flag gaps where the vault has no coverage.
8. **Decide whether to save:**
   - **The user passed `--no-save` or asked not to save** → write nothing, and end the answer by saying it was not saved at their request. This holds in non-interactive runs too (another tool calling `/b:qa --no-save`).
   - **One-line lookup** — a single fact, or a yes or no, taken from one note and fitting in one or two sentences → write nothing, and end the answer by saying it was not saved because it is a one-line lookup.
   - **Anything else is substantive** → save it (step 9) without asking.
9. **Save** to `content/_outputs/answers/YYYY-MM-DD_<topic>.md`, where `<topic>` is a short kebab-case slug. If that file exists, add `-2`, `-3`, … — never overwrite an earlier answer. Tell the user the path. The note:

   ```markdown
   ---
   title: "<the question, or a short title for it>"
   date: YYYY-MM-DD
   type: answer-note
   summary: "<the answer in one line>"
   gaps: <number of items in the gaps section; 0 when it says there are none>
   agent-created: true
   ---

   # <title>

   <the answer>

   ## <"What this rests on", in the vault language>

   - [[<Note A>]] — <what it contributed>
   - [[<Note B>]] — <what it contributed>
   - <Inference>: <which parts of the answer are your reasoning, not note content>

   ## <"Gaps", in the vault language>

   - <a part of the question the vault could not answer>
   - <Unresolved contradiction>: [[<Note C>]] — <subject>
   ```

   - **Inside the saved vault note, cite with `[[wikilinks]]`, not markdown links** — wikilinks are the vault convention, render in Obsidian, and feed `graph.md`. The markdown-link form is for the chat answer only.
   - The headings and labels are in the vault's primary language (from `content/WRITING_STYLE.md`); `gaps:` is a number, so scripts can count gaps whatever the language. When the vault answered everything, the gaps section says so in one line and `gaps: 0`.
   - `content/_outputs/` is outside the indexes, so saving needs no index update. `/b:gaps` lists saved answers whose `gaps:` is above zero.
10. Offer the user two follow-ups, and change no topic note unless they choose one:
    - Promote the answer to a full wiki article via the `brain-compile` skill.
    - File the new content back into existing notes via the `brain-enhance` skill.

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
`LIMITS.md` — read before telling the user the vault is sure of anything.
