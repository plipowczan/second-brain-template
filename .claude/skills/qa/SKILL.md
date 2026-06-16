---
name: qa
description: Use when user says "research X", "what do my notes say about X", "co mam w notatkach o X". Synthesizes an answer from the vault citing wikilinks; offers to save substantial answers to `_outputs/answers/`.
---

# Q&A

## When to use

Trigger phrases: "research X", "what do my notes say about X", "co mam w notatkach o X". The user wants an answer drawn from existing vault content.

## Workflow

1. Read `content/_indexes/vault-map.md` → identify relevant folders and tags for the question.
2. Read matching sections of `content/_indexes/catalog.md` → identify candidate notes.
3. Read `content/_indexes/graph.md` for link chains starting from candidates.
4. Read the actual note files — only the ones identified, not the whole vault.
5. Synthesize the answer, citing `[[sources]]` for every claim drawn from the vault. Clearly distinguish wiki content from inference. Flag gaps where the vault has no coverage.
6. If the answer is substantial, offer the user three follow-ups:
   - Save to `content/_outputs/answers/YYYY-MM-DD_<topic>.md` (type `answer-note`).
   - Promote to a full wiki article via the `compile` skill.
   - File the new content back into existing notes via the `enhance` skill.

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
