---
name: brain-ingest
description: Use when user says "ingest", "process inbox", "przetworz nowe pliki", or when files appear in `content/_raw/inbox/`. Turns raw sources into wiki notes across every note they touch: shows one plan (reading, notes to create and update, contradictions) before writing, marks contradictions instead of overwriting, records the final archive path as the source, updates all 3 indexes. `--batch` skips the plan.
---

# INGEST

## When to use

Trigger phrases: "ingest", "process inbox", "przetworz nowe pliki". Files have appeared in `content/_raw/inbox/` and need to be turned into wiki notes.

**Also accepts YouTube URLs as arguments:** `/b:ingest https://youtu.be/X https://www.youtube.com/watch?v=Y`. URLs and files can be mixed in one batch — they cluster together under the same logic.

**Batch mode:** `/b:ingest --batch` (or the user explicitly asks to ingest without review) skips the plan question. It is never switched on by you, whatever the number of sources.

## Workflow

Four phases. Phase 0 runs only when YouTube URLs are present as arguments. Phase 1 reads every source, maps it against the vault and ends with **one** message to the user: the plan, together with the cluster question if there are clusters. Nothing is written before the reply. Phase 2 writes autonomously. Phase 3 verifies and reports.

A source does not become one summary note. It becomes a main note plus an addition to every existing note it has something to say about — and the user sees that map before anything is written, because a misreading caught in the plan costs one reply, while a misreading written into five notes comes back in every later answer.

### Phase 0 — Arguments and YouTube fetch

1. Validate args. `--batch` switches on batch mode. Any token matching `^https?://(www\.|m\.)?(youtube\.com|youtu\.be)/` is a YT URL. Any other non-empty argument aborts the whole call with a clear error naming it, before any work begins.

The rest of Phase 0 is skipped entirely when there are no URLs.

2. Verify prerequisites:
   - `yt-dlp` (required). Don't pre-check it with `which`: `yt_fetch.py` finds it itself, trying `$YT_DLP_CMD`, then a `yt-dlp` on PATH that actually starts, then `python -m yt_dlp`. If the script exits 3 with `yt-dlp not found`, abort the whole call with the install hint (`pip install yt-dlp`).
   - `ffmpeg` on PATH (needed only for Whisper fallback).
   - `$WHISPER_CPP_BIN` + `$WHISPER_MODEL` env vars (needed only for Whisper fallback).
3. For each URL, run:

   ```bash
   python .claude/skills/brain-ingest/scripts/yt_fetch.py <url> --out-dir content/_raw/processed/
   ```

   On success, stdout is one-line JSON: `{video_id, title, archive_path, transcription, duration}`.
   On failure, exit code is 2 (bad URL) or 3 (fetch failure), with the reason on stderr. **Skip that URL and continue with the rest.** Collect failures for the final report.

4. Build a `Source` object per URL (in-memory, for Phase 1/2):

   ```
   Source { origin: "youtube", title, body=<archive file contents>, tokens (from title + chapters + first 2000 chars), meta (from frontmatter), raw_path=archive_path }
   ```

5. Inbox files (if any) also yield `Source` objects with `origin: "file"`. Phase 1 operates on the union.

**Idempotency check.** Before fetching, scan `content/_indexes/catalog.md` and the topic-folder notes for any frontmatter with the same `video_id`. If a match exists, skip Phase 0 fetch for that URL and feed the existing source path into Phase 1 as an existing note to update.

The transcripts Phase 0 archives into `content/_raw/processed/` are the only files written before the plan is answered: the plan needs them.

### Phase 1 — Read, map, plan

1. Read `content/_indexes/vault-map.md` to understand current vault structure.
2. List `content/_raw/inbox/` AND merge in any `Source` objects built by Phase 0. If both are empty, report "Inbox empty and no URLs provided, nothing to process" and exit.
3. **Batch mode only:** before touching the first source, tell the user that batch mode runs without the plan review and that its notes come out thinner than reviewed ones, because nobody corrects your reading of the sources.
4. **Read each source end to end** before forming a view of it. Note what it is (article, transcript, thread, notes) and who wrote it.
5. **Cluster detection.** For each pair of sources (file or YT):
   - Tokenize titles (or YT video titles): split on spaces, hyphens, underscores; lowercase; drop stop-words of the vault language and of the source language.
   - Read the first ~200 characters of each source body (file content or transcript) for additional tokens. YT sources also contribute their channel name and chapter titles as tokens.
   - Group files sharing **≥2 distinctive tokens** OR one strong product-name token appearing in multiple titles.
   - A cluster requires **≥2 files** to form.
6. **Map each source against the vault.** Use `content/_indexes/catalog.md` to find candidate notes, `graph.md` to follow their links, and read every candidate you are about to list. Sort what the source touches into three groups:
   - **Main note** — the one note that carries the source's main subject: an existing note (overlap → it is updated) or a new one.
   - **Existing notes to add to** — notes that exist and to which the source adds a fact, a figure, an example or a counter-claim. Write down, per note, what it gains.
   - **New notes** — subjects the source covers in enough depth to stand alone, that have no note yet.

   A note the source only *mentions* gets a link from the main note, not an addition. There is no quota: a source that adds to no other note is fine, and the report says why.
7. **Check for contradictions.** For the main note (if it exists) and every existing note in the map, compare what the source says with what the note claims. List every conflict: the note, its claim, and the source's claim.
8. **Send the user one message** for the whole run. It holds the cluster block (only if clusters exist), then one plan block per source:

   ```
   Cluster "<name>" (<N> files):
     - <filename>   [parent candidate]   ← only if title lacks team/repo slash pattern but shares cluster tokens
     - <filename>   [repo]
     ...
   Options:
     A) Separate tool notes (CLAUDE.md default — each repo gets own note)
     B) Parent hub note + children (knowledge-note + N tool notes, bidirectional links)
     C) Custom — describe

   1. <source file name or video title>
      Claims:      <what the source argues, one sentence>
      Create:      [[<Main note>]] (main), [[<New note>]]
      Add to:      [[<Existing note>]] — <what it gains>; [[<Other note>]] — <what it gains>
      Contradicts: [[<Existing note>]]: "<its claim>" vs "<the source's claim>"   (or: none found)
   2. ...

   Reply OK to write this, or correct it: a different reading, a note to leave alone, a cluster choice. Reply "cancel" to stop.
   ```

   Mark an existing main note as `(main, update)` instead of `(main)`. Write the block in the vault language.
9. **Wait for the reply**, then write according to the plan as confirmed or corrected. If the user cancels: write no note and no index, leave every inbox file where it is, and report that nothing was ingested (name any transcripts Phase 0 already archived).

**In batch mode** skip steps 8–9: resolve every cluster with option A (separate notes) and go straight to Phase 2 with the plan you built.

### Phase 2 — Execute

For each source (cluster handling per the user's choice from Phase 1), following the plan:

1. Determine topic folder and note type per CLAUDE.md rules (sub-patterns: `BOOKS/`, `TOOLS/`, `KNOWLEDGE/INFO/`, `KNOWLEDGE/HOWTO/`, `NOTES/`, `HABITS/`). For YT-origin sources, classification input is `title + description + channel + chapter titles + first ~2000 chars of transcript`. YT-origin sources always use `type: knowledge-note` with template `templates/knowledge_note_info.md`.

   **Language enforcement:** The canonical vault language is whatever this vault's writing-style document declares as its primary language — `content/WRITING_STYLE.md`, or `content/WRITING_STYLE_ANALYSIS.md` in vaults that predate the onboarding template (AGENTS.md "Writing Style" points at whichever this vault uses). Read whichever exists before writing — never assume a language. If the source content is in another language, **translate it into the vault language while ingesting**. This applies to: body prose, frontmatter `title` / `summary` / `tags`, and any quoted material. Preserve verbatim: proper nouns (vendor/product/person/place names), established technical terms, code blocks, URLs, dates, wikilinks, emoji.
2. **Choose the archive path before writing anything.** File sources: `_raw/processed/YYYY-MM-DD_<originalname>.<ext>` (today's date). If that name is taken, add `-2`, `-3`, … before the extension. YT sources: the `archive_path` from Phase 0. This path, relative to `content/`, is the source reference for every note this source touches. Never write a `_raw/inbox/` path into a note: the file will not be there after this run.
3. **Source fields.** A note records its sources in `source:` (one value) or `sources:` (a list). The note templates may not show these fields; fill them yourself:
   - New note: `sources: ["<archive path>"]`.
   - Existing note with `sources:`: append the archive path.
   - Existing note with `source:`: replace it with `sources:`, the earlier value first, then the archive path.
   - Existing note with neither: add `sources: ["<archive path>"]`.

   Other values (URLs, a description such as "Call with the vendor") stay as they are.
4. **Write the main note.** New: create it from the appropriate template under `content/templates/` (per CLAUDE.md "Templates" table). Existing: merge into it, preserving all user-authored content. Fill frontmatter: `title`, `date` (today, new notes only), `tags`, `type`, the source fields from step 3, `agent-created: true` (new notes), `summary:` (one line).

   For YT-origin notes, the following YT-specific fields are appended:

   ```yaml
   source_url: "https://www.youtube.com/watch?v=<video_id>"
   video_id: "<id>"
   channel: "<channel name>"
   duration: "1h23m"
   published: 2026-04-15
   transcription: captions   # or "whisper-large-v3"
   ```

   Note body uses adaptive depth based on transcript duration:
   - `< 15 min` → summary: TL;DR, 5-10 key points, takeaways, Resources.
   - `15-45 min` → standard knowledge-note structure with sections, quotes, takeaways.
   - `> 45 min` → deep note: chapter-by-chapter breakdown with `[mm:ss]` timestamps linking to `https://youtube.com/watch?v=<id>&t=<seconds>s`.
5. **Write the new notes** from the plan the same way.
6. **Add to every existing note in the plan.** Add only what this source adds to that note, keep everything that is there, record the archive path in its source fields (step 3), and link it to the main note — and the main note back to it. Notes the source only mentions get a link from the main note, nothing more.
7. **Mark contradictions, never overwrite.** When the source conflicts with a claim a note makes, keep the claim's text as it is and put a callout next to it:

   ```markdown
   > [!contradiction] <short subject>
   > <Earlier>: <the note's claim> (source: <its source, if known>)
   > <New>: <the source's claim> (source: <archive path>)
   ```

   The callout type is always the English word `contradiction`; the title and the labels (`Earlier` / `New`) are in the vault language. Never delete or rewrite the earlier claim to match the new source — only the owner decides which claim holds.
8. Add wikilinks to related notes; update those target notes to backlink.
9. **Move attachments.** Find image/media files referenced by the source (`.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webm`, `.pdf`, etc.) that landed in `content/` root or `content/_raw/inbox/`. Move them to `content/ATTACHMENTS/`. Update any `![[filename]]` references in the new note to point to the moved location.
10. Move source:
    - File sources: `content/_raw/inbox/<file>` → the archive path chosen in step 2.
    - YT sources: archive file already lives in `content/_raw/processed/` from Phase 0 — no move needed.
11. Update all three indexes per CLAUDE.md auto-update rules, for **every** note this run created or changed:
    - `catalog.md` — add or update the entry line in the correct folder section.
    - `vault-map.md` — increment folder count, refresh top-tags, prepend to Recent Changes.
    - `graph.md` — add outgoing links for each changed note; update incoming-link entries on every target note.

Phase 2 is autonomous. No per-file confirmation. The plan and the cluster decisions were already settled in Phase 1.

### Phase 3 — Final Checklist

1. Re-read `vault-map.md`:
   - Does `total_notes` match the delta (old count + new notes − merges)?
   - Are all new notes present in `Recent Changes`?
2. Spot-check `catalog.md` — every new note has an entry line in its folder section.
3. **Every source path exists.** For every note this run created or changed, check that each `_raw/` path in its `source:` / `sources:` exists under `content/`, and that none points to `_raw/inbox/`. Fix any that does not before reporting; if you cannot, report it as a failure.
4. Print the final report. One block per source lists **every** note it touched:

   ```
   Ingest complete.
   - Processed: X sources (F files, Y YouTube URLs)
   - Notes:     N created, M updated
   - Contradictions marked: K
   - Attachments moved: W
   - YouTube:   captions=A, whisper=B, failed=C
   - Indexes:   ✅ vault-map / catalog / graph

   <source 1> → _raw/processed/<archive name>
     Main:     [[<Main note>]] (created | updated)
     Created:  [[<New note>]]
     Updated:  [[<Existing note>]], [[<Other note>]]
     Marked:   [[<Existing note>]] — contradiction on <subject>
     Only one note changed: <why — e.g. no other note covers this subject yet>
   <source 2> → ...

   Failures (if any):
     - <url or file> — <reason>
   Inbox now empty.
   ```

   The "Only one note changed" line appears only when it applies. **In batch mode**, replace the per-source blocks with a table — `| Source | Main note | Other notes changed | Status |` — followed by the totals.

If the checklist fails, surface the discrepancy and offer to fix before reporting completion.

## Failure Handling

| Failure | Behavior |
|---|---|
| Argument is neither `--batch` nor a YT URL | Abort whole `/b:ingest` call before Phase 0; name the argument. |
| `yt-dlp` not found (`yt_fetch.py` exits 3: `yt-dlp not found`) | Abort whole call with install hint. |
| Video unavailable / private / removed | Skip that URL, continue rest. Final report flags it. |
| No captions AND Whisper fallback fails | Skip that URL. Final report names which step failed. |
| Captions 429 / per-language failure | `yt_fetch.py` iterates languages individually with 15s back-off retry on HTTP 429, so a rate-limited or missing language no longer aborts the whole captions step. |
| User cancels the plan | Nothing written, inbox untouched; report "nothing ingested" and any transcripts already archived. |
| Classification ambiguous | Best-guess folder + `#todo/classification` tag (existing fallback). |
| Archive name already taken | Add `-2`, `-3`, … before the extension; write that name into the notes. |
| A written source path does not exist at the checklist | Fix it before reporting; if impossible, list it under Failures. |
| Network/timeout during fetch | `yt_fetch.py` returns non-zero; skill skips that URL. |
| Phase 0 succeeds, Phase 2 fails mid-note | Transcript archive already in `_raw/processed/`; rerun targets it for completion. |

## Prerequisites

- `yt-dlp` — required for any YT URL. `pip install yt-dlp` is enough: when the `yt-dlp` executable is missing or won't start, `yt_fetch.py` runs `python -m yt_dlp` with the interpreter it runs under. That covers Windows Smart App Control, which blocks pip's unsigned `yt-dlp.exe` but lets the signed `python.exe` run. To force a specific command, set `$YT_DLP_CMD` (for example `"C:\Program Files\yt-dlp\yt-dlp.exe"`; double-quote paths with spaces). It is used as given, without the start-up check.
- `ffmpeg` on PATH — required only when captions are unavailable (Whisper fallback).
- `$WHISPER_CPP_BIN` + `$WHISPER_MODEL` env vars — required only for Whisper fallback. Default model: `ggml-large-v3.bin`.

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
CLAUDE.md "Templates" table — for the type → template mapping used in Phase 2.
`LIMITS.md` — why the plan step exists, and what batch mode costs.
