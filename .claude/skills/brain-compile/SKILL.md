---
name: brain-compile
description: Use when user says "compile X", "write article about X", "napisz artykuł o X". Synthesizes a new wiki article from existing notes on a topic, citing them as wikilinks, type `compiled-note`; keeps disagreements between notes visible as contradiction callouts.
---

# COMPILE

## When to use

Trigger phrases: "compile X", "write article about X", "napisz artykuł o X". The user wants a synthesized wiki article on topic X, drawing from notes already in the vault.

## Workflow

1. Read `content/_indexes/vault-map.md` → `catalog.md` → relevant notes for topic X.
2. Follow `graph.md` link chains for related content.
3. Write a synthesized article using the closest matching template, citing sources as `[[wikilinks]]`.
   **Mark contradictions, never smooth them over.** When the notes you compile from disagree, keep both claims in the article and put a callout where they meet:

   ```markdown
   > [!contradiction] <short subject>
   > <Earlier>: <one claim> (source: [[<note>]])
   > <New>: <the other claim> (source: [[<note>]])
   ```

   The callout type is always the English word `contradiction`; the title and labels are in the vault language. Carry over any `> [!contradiction]` callout from a source note that bears on the article. Do not pick a side for the owner, and list every callout in your summary to the user.
4. Set frontmatter: `type: compiled-note`, `agent-created: true`, and a one-line `summary:`. If you cite raw source files directly, list their `_raw/processed/` paths in `sources:`.
5. Place the article in the appropriate topic folder under `content/`.
6. Update cited notes to link back to the new article. Update all three indexes (`vault-map.md`, `catalog.md`, `graph.md`) per the auto-update rules in CLAUDE.md.

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
