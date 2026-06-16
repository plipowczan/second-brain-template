---
title: "Example Note"
date: 2026-06-15
enableToc: true
openToc: true
tags: ["knowledge", "example"]
type: knowledge-note
agent-created: true
summary: "A worked example note showing the conventions this knowledge base uses."
---

# Example Note 📒

This is a worked example. It exists so the management skills (`/qa`, `/lint`,
`/enhance`, `/reindex`) have real content to operate on the moment you open the
template. When you run onboarding you will be offered the chance to delete the
whole `REFERENCE/` folder.

## 🗒️ What a note looks like

Every note in this knowledge base starts with YAML frontmatter: a `title`, a
`date`, a `type`, a short `summary`, and a list of `tags`. The body uses
hierarchical headings and bulleted lists, and ends with a Resources section.

- Keep one idea per note.
- Prefer short, descriptive titles — the filename is what wikilinks resolve to.
- Tag consistently; the indexes build a tag cloud from these.

## 🔗 How notes connect

Notes link to each other with wikilinks. See [[Wikilinks Explained]] for how
they resolve and why the filename has to match the link text.

## 📖 Resources

- [[Wikilinks Explained]]
- Template used: `content/templates/knowledge_note_info.md`
