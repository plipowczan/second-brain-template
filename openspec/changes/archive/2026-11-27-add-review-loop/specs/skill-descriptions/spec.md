# Spec Delta

## Purpose

Defines the shape of a skill's description and body, so that the agent picks the right
skill among overlapping ones and every skill ends in a predictable result, while the
descriptions that enter every session stay short.

## ADDED Requirements

### Requirement: New skills and skills whose behaviour changes follow the pattern

A skill added after this change, and a skill whose behaviour the owner sees change
(`brain-ingest` in this change), SHALL have a single-quoted description that starts with
"Use when" and its trigger phrases, says in one sentence what it does and writes, and
names an overlapping neighbour after "Do NOT use for". Its body SHALL have a
`## Calibration` section (the typical failure, what right looks like) and SHALL state its
output shape. `CONTRIBUTING.md` SHALL describe the pattern.

#### Scenario: Review and lint
- **WHEN** an agent reads the descriptions of `brain-review` and `brain-lint`
- **THEN** each names the other after "Do NOT use for", so a request for a health audit goes to lint and a request for a look back goes to the review

### Requirement: Descriptions cannot grow without notice

`dev/build_codex_files.py --check` SHALL fail when a skill's description is longer than
500 characters, in addition to its existing checks.

#### Scenario: Long description
- **WHEN** a contributor writes a 520-character description
- **THEN** the check fails and names the skill and the length
