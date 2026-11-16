---
name: brain-gaps
description: Use when the user says "find gaps", "what's missing", "coverage analysis", "where is my vault thin". Surfaces weakly-connected notes, topics implied but never written, and stale clusters — an actionable to-build map.
---

# GAPS

## When to use

The user wants to know where the knowledge base is incomplete — not mechanical
issues (that is `/b:lint`), but *knowledge* gaps.

## Workflow

1. Ensure the indexes are fresh (run `/b:reindex` if stale).
2. Get structural signals (run from the repo root):
   ```bash
   python .claude/skills/brain-gaps/scripts/gaps.py
   ```
   This returns weakly-connected notes (link degree ≤ 1) — candidates that are
   under-linked into the rest of the vault — and `answer_gaps`: saved Q&A answers in
   `content/_outputs/answers/` whose `gaps:` count is above zero, newest first. Each
   is a question the vault could not fully answer; open the answer to read its gaps
   section.
3. Read `content/_indexes/catalog.md` and `content/_indexes/vault-map.md` and
   reason over them together with the signals to identify:
   - **Weakly-connected notes** — should they link to existing notes?
   - **Implied-but-missing topics** — notes that reference a concept that has no
     note of its own.
   - **Thin areas** — folders/tags with very few notes relative to their importance.
   - **Stale clusters** — groups of old notes (cross-check `/b:lint` staleness).
   - **Unanswered questions** — the gaps recorded in the `answer_gaps` answers: what
     the owner asked and the vault could not answer, so the sources to find next.
4. Produce a short, prioritized "to-build / to-link" list. Offer to save it to
   `content/_outputs/reports/`.
