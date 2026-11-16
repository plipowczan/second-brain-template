# Spec Delta

## Purpose

Keeps a conflict between a new source and what the base already says visible in the note
itself, so that no skill silently replaces one claim with another and the owner can
decide.

## ADDED Requirements

### Requirement: Contradictions use one fixed marker

A contradiction SHALL be recorded in the note body as an Obsidian callout whose type is
`contradiction`: a first line `> [!contradiction]`, optionally followed by a short title,
and quoted lines that give:

- the claim the note made before, with its source;
- the new claim, with its source.

The callout type SHALL be the English word `contradiction` in every base. The title and
the labels SHALL be in the base's primary language.

#### Scenario: Marker in a Polish base
- **WHEN** ingest records a contradiction in a base whose primary language is Polish
- **THEN** the note contains a callout that starts with `> [!contradiction]`, with Polish labels for the earlier claim and the new claim, each with its source

### Requirement: Writing skills mark contradictions and never overwrite

When new material conflicts with a claim a note already makes, brain-ingest,
brain-enhance and brain-compile SHALL keep the existing claim's text, add a contradiction
marker next to it, and list every marker they added in their report. They SHALL NOT
delete or rewrite the earlier claim to match the new material.

#### Scenario: Conflicting figure
- **WHEN** a note says a plan costs 10 USD a month and a new source says 20 USD
- **THEN** the note still says 10 USD, a contradiction marker next to it gives both figures with their sources, and the ingest report lists the marker

### Requirement: Only the owner resolves a contradiction

A skill SHALL remove a contradiction marker, and rewrite the note to the claim that holds,
only after the owner has decided in the session which claim holds.

#### Scenario: Enhance meets a marker
- **WHEN** brain-enhance improves a note that carries a contradiction marker and the owner has not decided between the claims
- **THEN** the marker and both claims remain in the note

### Requirement: Q&A presents both sides

When a note that brain-qa uses for an answer carries a contradiction marker relevant to
the question, brain-qa SHALL present both claims with their sources and SHALL NOT choose
one without saying so. A saved answer SHALL list each unresolved contradiction among its
gaps.

#### Scenario: Question hits a marked claim
- **WHEN** the user asks for the plan's price and the note carries a contradiction marker about it
- **THEN** the answer gives both prices with their sources, and the saved answer lists the contradiction as a gap

### Requirement: Lint lists notes with markers

The lint scanner SHALL report every scanned note that contains at least one contradiction
marker, with the number of markers in it. It SHALL match the callout type regardless of
letter case, and SHALL NOT count markers inside fenced code blocks. This report SHALL be a
warning (see the `lint-report` capability).

#### Scenario: Two markers
- **WHEN** a note contains two `> [!contradiction]` callouts
- **THEN** the scanner lists that note once, with the count 2

#### Scenario: Example in a code block
- **WHEN** a note shows the marker format only inside a fenced code block
- **THEN** the scanner does not list that note
