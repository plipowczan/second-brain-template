---
name: compile
description: Use when user says "compile X", "write article about X", "napisz artykuł o X". Synthesizes a new wiki article from existing notes on a topic, citing them as wikilinks, type `compiled-note`.
---

# COMPILE

## When to use

Trigger phrases: "compile X", "write article about X", "napisz artykuł o X". The user wants a synthesized wiki article on topic X, drawing from notes already in the vault.

## Workflow

1. Read `content/_indexes/vault-map.md` → `catalog.md` → relevant notes for topic X.
2. Follow `graph.md` link chains for related content.
3. Write a synthesized article using the closest matching template, citing sources as `[[wikilinks]]`.
4. Set frontmatter: `type: compiled-note`, `agent-created: true`, and a one-line `summary:`.
5. Place the article in the appropriate topic folder under `content/`.
6. Update cited notes to link back to the new article. Update all three indexes (`vault-map.md`, `catalog.md`, `graph.md`) per the auto-update rules in CLAUDE.md.

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
