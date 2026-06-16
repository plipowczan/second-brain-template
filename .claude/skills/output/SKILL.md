---
name: output
description: Use when user says "generate report about X", "create summary of X", "stwórz podsumowanie X". Generates a requested format (summary, reading list, topic map, timeline) and saves to `_outputs/` or topic folder.
---

# OUTPUT

## When to use

Trigger phrases: "generate report about X", "create summary of X", "stwórz podsumowanie X". The user wants a derived artifact built from vault content — not a full new wiki article (that is COMPILE), but a focused report or summary.

## Workflow

1. Research the topic using the indexes: `vault-map.md` → `catalog.md` → `graph.md`.
2. Generate the requested format. Common formats include:
   - Summary (prose distillation).
   - Reading list (ordered list of notes with one-line annotations).
   - Topic map (hierarchical outline).
   - Timeline (chronological view).
3. Save the artifact:
   - Default: `content/_outputs/<format>/YYYY-MM-DD_<topic>.md`.
   - If the user wants it published as wiki content: appropriate topic folder, with proper frontmatter and `type:`.
4. Update all three indexes if the artifact was published to the wiki.

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
- `compile` skill — for full wiki articles (different output type).
