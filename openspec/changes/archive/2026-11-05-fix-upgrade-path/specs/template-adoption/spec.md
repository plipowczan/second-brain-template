## ADDED Requirements

### Requirement: Adoption carries executable bits

Adoption SHALL treat the executable bit as an upgrade does, using the `executable` list of
the source's manifest, also when the nearest release R is older than the source. Adoption
SHALL NOT remove a bit.

#### Scenario: Adoption brings the test that checks the hook
- **WHEN** an adoption adds `.github/workflows/tests.yml` and `.githooks/pre-commit` has mode `100644` in `HEAD`
- **THEN** the plan offers the bit, and after the adoption commit the hook has mode `100755`, so the test passes on Linux without an upgrade

#### Scenario: Adoption adds a listed file
- **WHEN** an adoption adds a listed file the instance lacks
- **THEN** the adoption commit records it with mode `100755`

#### Scenario: Nearest release older than the list
- **WHEN** R is `0.1.0`, which shipped the hook with mode `100644`
- **THEN** the plan still offers the bit, because the mode only ever moves forward
