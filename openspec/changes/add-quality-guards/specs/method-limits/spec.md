# Spec Delta

## Purpose

Tells the agent and the owner where this way of keeping knowledge fails and what to do
about each failure, in a file that reaches every base and that the skills read before
they speak with confidence.

## ADDED Requirements

### Requirement: The template ships a limits file

The template SHALL contain a root file `LIMITS.md` that names these failure modes and,
for each one, what the owner and the agent do about it:

- errors compound: a wrong note feeds an answer, the answer is filed back, and two notes
  then agree on the error;
- a citation looks like proof but only shows that a file name was written next to a
  claim;
- the context ceiling: past some size the indexes stop being a sufficient map;
- every operation costs tokens, and careful operations cost more;
- the whole base is one model's reading of the sources.

It SHALL also say that a tidy base is not the same as a correct one.

#### Scenario: Every failure mode has an action
- **WHEN** a reader opens `LIMITS.md`
- **THEN** each of the five failure modes is named and followed by at least one concrete action

### Requirement: The limits file reaches every base

The manifest SHALL list `LIMITS.md` in the owned class, so that onboarding keeps it and
brain-upgrade adds it to bases that do not have it.

#### Scenario: Manifest check
- **WHEN** the manifest check runs on the template repository
- **THEN** `LIMITS.md` is classified as owned and the check passes

#### Scenario: Upgrade of an older base
- **WHEN** a base on version `0.2.1` without `LIMITS.md` is upgraded to the release that contains it
- **THEN** the upgrade plan adds `LIMITS.md`

### Requirement: Q&A and lint read the limits before claiming certainty

brain-qa and brain-lint SHALL read `LIMITS.md` before they state that the base is sure,
complete or consistent about anything, and SHALL name the limits that apply to that
statement. When the file is missing, they SHALL say so and SHALL NOT claim certainty.

#### Scenario: Question about certainty
- **WHEN** the user asks whether the notes settle a question and the answer rests on one note citing one source
- **THEN** brain-qa says that the answer rests on a single source and names the matching limit from `LIMITS.md`

### Requirement: Agent instructions point to the limits file

The agent instruction template SHALL point to `LIMITS.md` in one line, so that agents
outside Claude Code that read `AGENTS.md` find it too.

#### Scenario: Fresh base
- **WHEN** onboarding renders `AGENTS.md` for a new base
- **THEN** the rendered file mentions `LIMITS.md`
