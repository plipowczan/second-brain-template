# learning-sessions Specification

## Purpose
Defines `/b:learn`: checking what the owner knows of their own notes, by a quiz or by
explaining a subject back, without changing the base.

## Requirements

### Requirement: Explain-back sorts every gap into one of three kinds

`/b:learn <topic or [[Note]]>` SHALL find the notes on the subject through the catalog,
explain the subject in plain words in one short paragraph, ask the owner to explain it
back, and compare that explanation with the notes. Each gap SHALL be reported as one of:
the base lacks it, its sources lack it, or the owner missed it.

#### Scenario: Owner leaves out a point a note makes
- **WHEN** the note names three conditions and the owner's explanation names two
- **THEN** the missing condition is reported as "you missed it", with the note named

### Requirement: The three kinds of gap have fixed meanings

"The base lacks it" SHALL mean that no note covers the point. "Its sources lack it" SHALL
mean that a note claims the point but the archived source that note cites does not
support it; to decide this the skill SHALL read only the sources the notes in use cite.
"You missed it" SHALL mean that a note has the point and the owner's explanation does
not.

#### Scenario: Claim without support in its source
- **WHEN** a note states a figure that the transcript it cites does not contain
- **THEN** the gap is reported as "its sources lack it", naming the note and the source

### Requirement: The quiz grades every answer against a named note

`/b:learn --quiz <topic> [N]` SHALL ask N questions (5 when omitted), one at a time,
mixing recall, why and application questions drawn from the notes, SHALL grade each
answer against the note the question came from and name that note, and SHALL end with the
score and the notes to revisit.

#### Scenario: Wrong answer
- **WHEN** the owner's answer contradicts the note
- **THEN** the grade says so and quotes the note's claim with the note named

### Requirement: A session is saved and changes no note

Each completed session SHALL be saved to `content/_outputs/learning/YYYY-MM-DD_<topic>.md`
(created on first use, never overwriting an earlier file, the topic slug checked against
the private terms as log paths are) with the mode, the notes used, the owner's
explanation or answers, the gaps by kind and the score, and SHALL append one `learn` row
to the log. Without a person present the skill SHALL stop before asking anything and
write nothing.

#### Scenario: Unattended run
- **WHEN** `/b:learn` runs from a script with no one to answer
- **THEN** it says it needs a person and writes no file

### Requirement: Gaps are offered back, never filed

The skill SHALL NOT write any note. A gap the base lacks SHALL only be offered as
`/b:compile` or an ingest of a source, and a gap its sources lack as `/b:enhance` on that
note.

#### Scenario: Gap the base lacks
- **WHEN** the owner explains a point no note covers
- **THEN** the skill offers `/b:compile` or an ingest and changes no note
