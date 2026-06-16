---
name: enhance
description: Use when user says "enhance [[Note]]", "improve X", "popraw notatkę X". Reads the note, fills gaps from related notes, adds bidirectional wikilinks, sets `agent-reviewed:` date, preserves all existing user-authored content.
---

# ENHANCE

## When to use

Trigger phrases: "enhance [[Note]]", "improve X", "popraw notatkę X". The user wants an existing note expanded or polished — never replaced.

## Workflow

1. Read the target note. Check `content/_indexes/catalog.md` and `graph.md` for context (what other notes reference this one, what related notes exist).
2. Identify gaps:
   - Empty `#todo`, `#todo/replace`, or `#todo/complete` sections.
   - Missing or incomplete frontmatter fields.
   - Missing wikilinks to obviously-related notes.
3. Fill content from related notes already in the vault. Cite where the new content came from.
4. Add bidirectional wikilinks: outgoing from this note to its targets, and update target notes to link back. Set `agent-reviewed: YYYY-MM-DD` (today) in frontmatter.
5. **Preserve all existing user-authored content.** Only add, never remove. If something looks wrong, flag it instead of editing it out.
6. Update all three indexes per CLAUDE.md auto-update rules.

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
