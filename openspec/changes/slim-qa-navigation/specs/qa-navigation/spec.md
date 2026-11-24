# Spec Delta

## Purpose

Defines how brain-qa and the agent instructions find the notes that answer a question,
so that a question costs a search of the indexes, not a full read of them on every call,
while the vault is still searched thoroughly before the agent says it does not cover the
question.

## ADDED Requirements

### Requirement: Q&A finds candidates by searching the catalog with a pattern

brain-qa SHALL start a question by searching `content/_indexes/catalog.md`
case-insensitively with a pattern built from the question's key terms, in the vault's
primary language and in the question's language, with synonyms and the words a note
title would use, and SHALL read only the matching lines. At this step it SHALL NOT read
the catalog or any of its sections whole, and SHALL NOT read `vault-map.md`. When the
first pattern finds nothing useful, it SHALL try a broader one.

#### Scenario: Question in another language than the vault
- **WHEN** the vault is written in English and the user asks in another language about a topic a note covers
- **THEN** brain-qa searches the catalog with a pattern that holds the English words a note title would use, and finds the note from the matching catalog line without reading the vault map or a catalog section

### Requirement: Map, catalog sections and note search are the fallback

Only when the catalog patterns find nothing SHALL brain-qa read the folder table of
`content/_indexes/vault-map.md` (skipping the read when the map is already in its
context), then the matching folder sections of `catalog.md`, then search the notes under
`content/` directly. It SHALL NOT say that the vault does not cover the question before
all three found nothing. A catalog section too large to read in full SHALL be reported
as a gap in the answer.

#### Scenario: Question the vault does not cover
- **WHEN** no catalog pattern matches the question
- **THEN** brain-qa checks the map's folder table, the matching catalog sections and the notes themselves, and only then says that the vault does not cover the question

#### Scenario: Map already in context
- **WHEN** the session-start hook has already put `vault-map.md` in the agent's context and the catalog patterns find nothing
- **THEN** brain-qa uses that map and does not read the file again

### Requirement: Q&A searches the link graph, never reads it whole

brain-qa SHALL use `content/_indexes/graph.md` only when the question needs links (how
notes connect, or a candidate that rests on another note), SHALL search it for the
candidate's title and follow the chain, and SHALL NOT read it whole.

#### Scenario: Question about how two notes connect
- **WHEN** the user asks how two notes the vault holds relate
- **THEN** brain-qa searches `graph.md` for their titles and follows the links it finds, without reading the whole file

### Requirement: Q&A reads the limits file only before claiming certainty

brain-qa SHALL apply these rules to every answer without reading `LIMITS.md`: a claim
from one note that cites one source is that source's view; two notes that agree may rest
on the same source; a relevant note it did not read is a gap, not support. It SHALL read
`LIMITS.md` before it says that the vault is sure, complete or consistent about
something, or when the user asks how far to trust the answer, and SHALL then name the
limits that apply. When the file is missing then, it SHALL say so and SHALL NOT claim
certainty.

#### Scenario: Ordinary question
- **WHEN** the user asks a question and the answer makes no claim of certainty
- **THEN** brain-qa answers without reading `LIMITS.md`, and still presents a claim from one note citing one source as that source's view

#### Scenario: Question about certainty
- **WHEN** the user asks whether the notes settle a question
- **THEN** brain-qa reads `LIMITS.md` before answering and names the limits that apply

### Requirement: The q&a command carries the skill text

The `/b:qa` command file SHALL include the text of `.claude/skills/brain-qa/SKILL.md` by
file reference and SHALL tell the agent not to load the skill again. The skill text SHALL
live only in that `SKILL.md`. A question asked without the command SHALL reach the same
workflow through the skill.

#### Scenario: Question through the command
- **WHEN** the user runs `/b:qa` with a question in Claude Code
- **THEN** the agent follows the brain-qa workflow from the included text without a separate call that loads the skill

#### Scenario: Question without the command
- **WHEN** the user asks "what do my notes say about X" without the command, or works in Codex, which has no commands
- **THEN** the agent loads the brain-qa skill by its description and follows the same workflow

### Requirement: Agent instructions start a question from the catalog

The Navigation Protocol in `AGENTS.template.md` SHALL tell the agent to read
`vault-map.md` first only for an operation that writes or reorganizes notes, unless the
map is already in its context; to start a question from the catalog, searched with a
pattern built from the question's key terms in the vault's language and the question's,
with synonyms; to read a catalog folder section only when the patterns find nothing; to
search `graph.md` for a note's title instead of reading it whole; and to search the notes
under `content/` directly only after the catalog found nothing.

#### Scenario: Fresh base
- **WHEN** onboarding renders `AGENTS.md` for a new base
- **THEN** its Navigation Protocol says that a question starts from a pattern search of `catalog.md`, and that `vault-map.md` is read first only for an operation that writes or reorganizes notes
