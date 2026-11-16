---
name: brain-enhance
description: Use when user says "enhance [[Note]]", "improve X", "popraw notatkę X". Reads the note, fills gaps from related notes, adds bidirectional wikilinks, sets `agent-reviewed:` date, preserves all existing user-authored content, marks contradictions instead of overwriting.
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
3. Fill content from related notes already in the vault. Cite where the new content came from. When you cite a raw source file, put its `_raw/processed/` path in the note's `source:` (one value) or `sources:` (a list); a note with `source:` that gains a second source gets `sources:`, the earlier value first.
4. Add bidirectional wikilinks: outgoing from this note to its targets, and update target notes to link back. Set `agent-reviewed: YYYY-MM-DD` (today) in frontmatter.
5. **Preserve all existing user-authored content.** Only add, never remove. If something looks wrong, flag it instead of editing it out.
6. **Mark contradictions, never overwrite.** When material from another note conflicts with a claim this note makes, keep the claim's text and put a callout next to it:

   ```markdown
   > [!contradiction] <short subject>
   > <Earlier>: <this note's claim> (source: <its source>)
   > <New>: <the conflicting claim> (source: [[<other note>]] or its source path)
   ```

   The callout type is always the English word `contradiction`; the title and labels are in the vault language. An existing `> [!contradiction]` callout stays, with both claims, until the owner decides in the session which claim holds — only then rewrite the note to that claim and remove the callout. List every callout you added in your summary to the user.
7. Update all three indexes per CLAUDE.md auto-update rules.

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
