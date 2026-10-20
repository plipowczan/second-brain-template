# Spec Delta

## Purpose

Makes one source update every note it has something to say about, instead of producing
one summary note per source, and makes the ingest report show all of those changes.

## ADDED Requirements

### Requirement: Ingest maps each source against the base

For each source, brain-ingest SHALL build a map from the catalog, the graph and the
candidate notes it reads, with three groups:

- the **main note**: the one note that carries the source's main subject, new or
  existing;
- **existing notes to add to**: notes that exist and to which the source adds a fact, a
  figure, an example or a counter-claim;
- **new notes**: subjects the source covers in enough depth to stand alone that have no
  note yet.

A note that the source only mentions SHALL get a link from the main note, not an
addition. The plan (see the `ingest-plan` capability) SHALL show this map.

#### Scenario: Source touches several existing notes
- **WHEN** a source about a tool's pricing change also gives a new benchmark that an existing comparison note covers and corrects a date in a timeline note
- **THEN** the map has the tool's note as the main note and the comparison and timeline notes as existing notes to add to

#### Scenario: Passing mention
- **WHEN** a source names a person once without saying anything new about them, and the base has a note about that person
- **THEN** that note is not in the group of notes to add to, and the main note links to it

### Requirement: Every affected note receives what the source adds

For each existing note in the map, brain-ingest SHALL:

- add only what the source adds to that note, and keep all existing content;
- record the source in that note's source fields (see the `source-traceability`
  capability);
- add a link from that note to the main note, and from the main note back to it.

#### Scenario: Addition to an existing note
- **WHEN** ingest adds a benchmark figure from a source to an existing comparison note
- **THEN** the comparison note keeps its earlier text, gains the figure, lists the source's archive path among its sources, and links to the main note, which links back

### Requirement: The report lists every changed note

brain-ingest's final report SHALL list, per source, the main note and every other note it
created or changed, and every contradiction marker it added. When a source changed only
one note, the report SHALL give the reason, such as no other note covering the subject.

#### Scenario: One note changed
- **WHEN** a source changes only its main note
- **THEN** the report names that note and states why no other note was changed

#### Scenario: Several notes changed
- **WHEN** a source creates one note and adds to three existing notes
- **THEN** the report lists all four notes under that source, each marked as created or changed

### Requirement: Indexes cover every changed note

After a run, the catalog, vault map and graph SHALL reflect every note that brain-ingest
created or changed, including the links it added to existing notes.

#### Scenario: New links appear in the graph
- **WHEN** ingest links three existing notes to a new main note
- **THEN** the graph lists the outgoing and incoming links of all four notes
