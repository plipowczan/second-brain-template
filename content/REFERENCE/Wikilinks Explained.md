---
title: "Wikilinks Explained"
date: 2026-06-15
enableToc: true
openToc: true
tags: ["knowledge", "example"]
type: knowledge-note
agent-created: true
summary: "How wikilinks resolve in this vault and why filenames must match link text."
---

# Wikilinks Explained 🔗

Wikilinks are how notes reference each other. They look like `[[Note Title]]`
and render as a clickable link to the note whose **filename** matches that
title.

## 🧩 Resolution rules

- A link `[[Wikilinks Explained]]` resolves to the file
  `Wikilinks Explained.md`, regardless of which folder it lives in.
- If a link does not resolve, the usual cause is that the filename does not
  match the link text. Rename the file to match, then run `/reindex`.
- Use the shortest unambiguous form; add a folder path only when two notes
  share a title.

## ☘️ Why it matters

The link graph is what makes a pile of notes into a knowledge base. The
`/reindex` skill reads these links to build `graph.md`, and `/lint` reports
broken links and orphan notes. This note links back to [[Example Note]] so the
two form a small connected graph.

## 📖 Resources

- [[Example Note]]
- See `CLAUDE.md` → "Navigation Protocol" for how the indexes use links.
