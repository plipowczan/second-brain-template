# Spec Delta

## Purpose

Makes `brain-ingest` show what it understood from each source, and what it is about to
write, before it writes anything, so that a misreading is caught at its cheapest point.

## ADDED Requirements

### Requirement: Ingest presents a plan before it writes

Before it creates or changes any note or index, and before it moves any file out of
`content/_raw/inbox/`, brain-ingest SHALL present a plan with one entry per source:

- what the source claims, in one sentence;
- the notes it will create;
- the existing notes it will add to;
- each claim in the base that the source contradicts, with the note that makes it, or an
  explicit statement that it found none.

It SHALL then wait for the user's reply and write according to the plan as the user
confirmed or corrected it. YouTube transcripts that Phase 0 archives into
`content/_raw/processed/` before the plan are the only files it MAY write before the
reply, because the plan needs them.

#### Scenario: One file, no clusters
- **WHEN** the inbox holds one file that forms no cluster and the user runs `/b:ingest`
- **THEN** brain-ingest shows a plan entry for that file and stops, and no note, index or inbox file has changed until the user replies

#### Scenario: The user corrects the reading
- **WHEN** the user replies to the plan that the source argues something else, or that a listed note must not be touched
- **THEN** brain-ingest writes according to the corrected plan and leaves the excluded note unchanged

#### Scenario: The user cancels
- **WHEN** the user replies to the plan with a cancellation
- **THEN** no note or index is written, every inbox file stays in the inbox, and brain-ingest reports that nothing was ingested

### Requirement: Ingest asks at most once per run

brain-ingest SHALL put the plan and the cluster question in one message for the whole
run. After the user's reply it SHALL NOT ask further questions, except to report a
failure that stops the run.

#### Scenario: Clusters and plan together
- **WHEN** a run has five sources, three of which form a cluster
- **THEN** brain-ingest sends one message that holds the cluster options and the plan entries for all five sources, and asks nothing more after the reply

### Requirement: Batch mode is explicit and says what it costs

brain-ingest SHALL skip the plan question only in batch mode. Batch mode starts when the
user passes `--batch` or explicitly asks to ingest without review. It SHALL NOT start on
its own, whatever the number of sources. In batch mode brain-ingest SHALL:

- say, before it processes the first source, that batch notes come out thinner because
  nobody corrects the reading;
- still build the plan and use it to write;
- resolve each cluster as separate notes (the default option);
- end with a table that gives, for each source, its main note and the number of other
  notes it changed.

#### Scenario: Batch run
- **WHEN** the user runs `/b:ingest --batch` with twenty files in the inbox
- **THEN** brain-ingest first states that batch notes are thinner, asks no question, and ends with one table row per source

#### Scenario: Many files without batch
- **WHEN** the user runs `/b:ingest` without `--batch` with twenty files in the inbox
- **THEN** brain-ingest still presents the plan and waits for the reply

### Requirement: The batch flag is a valid argument

brain-ingest SHALL accept `--batch` alongside YouTube URLs. Any other argument that is
not a YouTube URL SHALL still abort the call before any work begins.

#### Scenario: Flag with a URL
- **WHEN** the user runs `/b:ingest --batch https://youtu.be/abc123`
- **THEN** brain-ingest fetches the video and processes it in batch mode

#### Scenario: Unknown argument
- **WHEN** the user runs `/b:ingest notes.md`
- **THEN** brain-ingest aborts before any fetch or write and names the argument it does not accept
