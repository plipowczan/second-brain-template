# onboarding-note-types Specification

## Purpose
Defines how the note types the owner chose at onboarding count as valid, without turning
the template's `schema.yml` into an edited file.

## Requirements

### Requirement: Lint accepts the note types chosen at onboarding

`lint_scan.py` SHALL accept as valid, besides the keys of `schema.yml`, every type listed
in `NOTE_TYPES` of `.kb-onboard.json` (a `|`-separated list), and SHALL enforce no
required field for a type that `schema.yml` does not list. A missing or unreadable
`.kb-onboard.json` SHALL change nothing. A `bad_type` finding in the `/b:lint` report
SHALL say that adding the type to `schema.yml` enforces its fields.

#### Scenario: Owner's own type
- **WHEN** `.kb-onboard.json` lists `recipe-note` and `schema.yml` does not
- **THEN** a note with `type: recipe-note` gets no `bad_type` and no `schema_violation` finding

#### Scenario: Type in neither file
- **WHEN** a note has a type listed neither in `schema.yml` nor in `NOTE_TYPES`
- **THEN** it is reported as `bad_type`, as before
