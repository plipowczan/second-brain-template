# Spec Delta

## Purpose

Keeps the answers `brain-qa` gives, and the questions the base could not answer, instead
of losing them when the session ends, and makes the open gaps easy to list.

## ADDED Requirements

### Requirement: Substantive answers are saved by default

brain-qa SHALL save every substantive answer, without asking, to
`content/_outputs/answers/YYYY-MM-DD_<topic>.md` as `type: answer-note`, and SHALL give
the user the saved path. When that file already exists, it SHALL save under a new name
and SHALL NOT overwrite the existing file. Inside the saved note, citations SHALL be
wikilinks.

#### Scenario: Synthesis from several notes
- **WHEN** the user asks a question whose answer draws on four notes
- **THEN** brain-qa answers, saves the answer under `content/_outputs/answers/` and states the path

#### Scenario: Same topic twice in a day
- **WHEN** brain-qa saves a second answer on the same topic on the same day
- **THEN** the first file is unchanged and the second answer is saved under a different name

### Requirement: One-line lookups are not saved, and the skill says so

brain-qa SHALL NOT save an answer that is a single fact or a yes or no taken from one
note and fits in one or two sentences. It SHALL then say that it did not save the answer,
and why.

#### Scenario: Quick check
- **WHEN** the user asks on what date a note says a tool was released
- **THEN** brain-qa gives the date, saves nothing, and says that a one-line lookup is not saved

### Requirement: The user can turn saving off

When the user passes `--no-save` or asks not to save, brain-qa SHALL write no file and
SHALL say that it did not save the answer at the user's request. This SHALL hold in
non-interactive runs too.

#### Scenario: Non-interactive query
- **WHEN** another tool runs brain-qa non-interactively with `--no-save`
- **THEN** no file is written under `content/` and the output says the answer was not saved on request

### Requirement: A saved answer shows its basis and its gaps

A saved answer SHALL have:

- frontmatter with the fields the schema requires for `answer-note`, and `gaps:` with the
  number of gaps as an integer;
- the answer;
- a section on what the answer rests on, which links every note used and says which
  parts are inference rather than note content;
- a section of gaps, which names each part of the question the base could not answer, or
  states that there are none.

The section headings SHALL be in the base's primary language. `gaps:` SHALL equal the
number of gaps listed, and SHALL be `0` when the section states that there are none.

#### Scenario: Answer with two gaps
- **WHEN** brain-qa saves an answer in a Polish base and the vault covers only part of the question
- **THEN** the note has Polish headings for its basis and its gaps, lists two gaps, and has `gaps: 2` in its frontmatter

### Requirement: Writing back into notes still needs the user's choice

After saving, brain-qa SHALL still offer to promote the answer with brain-compile and to
file its content into existing notes with brain-enhance. It SHALL NOT change topic notes
unless the user chooses one of these.

#### Scenario: Saved answer, no choice made
- **WHEN** brain-qa saves an answer and the user does not take up either offer
- **THEN** no note outside `content/_outputs/answers/` has changed

### Requirement: Gap listing includes saved answers

The gaps script SHALL list every saved answer whose `gaps:` value is greater than zero,
with its path, title, date and number of gaps, newest first. It SHALL skip answers
without a `gaps:` field, and SHALL report an empty list when there is no answers folder.

#### Scenario: Mixed answers
- **WHEN** the answers folder holds one answer with `gaps: 2`, one with `gaps: 0` and one older answer without `gaps:`
- **THEN** the gaps script lists only the first answer, with the count 2
