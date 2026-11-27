# Spec Delta

## MODIFIED Requirements

### Requirement: The batch flag is a valid argument

brain-ingest SHALL accept `--batch`, `--backlog` with an optional whole number of 1 or
more right after it, and YouTube URLs. Any other argument, including a number that does
not follow `--backlog`, SHALL abort the call before any work begins, and brain-ingest
SHALL name that argument.

#### Scenario: Flag with a URL
- **WHEN** the user runs `/b:ingest --batch https://youtu.be/abc123`
- **THEN** brain-ingest fetches the video and processes it in batch mode

#### Scenario: Backlog with a number
- **WHEN** the user runs `/b:ingest --backlog 5`
- **THEN** brain-ingest accepts both arguments and takes a batch of 5 sources

#### Scenario: A number without the backlog flag
- **WHEN** the user runs `/b:ingest --batch 5`
- **THEN** brain-ingest aborts before any fetch or write and names `5` as the argument it does not accept

#### Scenario: Unknown argument
- **WHEN** the user runs `/b:ingest notes.md`
- **THEN** brain-ingest aborts before any fetch or write and names the argument it does not accept
