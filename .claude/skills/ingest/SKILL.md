---
name: ingest
description: Use when user says "ingest", "process inbox", "przetworz nowe pliki", or when files appear in `content/_raw/inbox/`. Processes raw sources into wiki notes, handles intra-batch clustering with confirmation, updates all 3 indexes.
---

# INGEST

## When to use

Trigger phrases: "ingest", "process inbox", "przetworz nowe pliki". Files have appeared in `content/_raw/inbox/` and need to be turned into wiki notes.

**Also accepts YouTube URLs as arguments:** `/ingest https://youtu.be/X https://www.youtube.com/watch?v=Y`. URLs and files can be mixed in one batch — they cluster together under the same logic.

## Workflow

Four phases. Phase 0 runs only when YouTube URLs are present as arguments. Phase 1 ends with a single user prompt (cluster confirmation) if any clusters are detected; Phase 2 runs autonomously; Phase 3 verifies index integrity.

### Phase 0 — YouTube fetch (only if URL args)

Skipped entirely for files-only invocations.

1. Validate args. Any token matching `^https?://(www\.|m\.)?(youtube\.com|youtu\.be)/` is a YT URL. Any non-empty argument that doesn't match aborts the whole call with a clear error before any work begins.
2. Verify prerequisites:
   - `yt-dlp` on PATH (required) — if missing, abort the whole call with install hint.
   - `ffmpeg` on PATH (needed only for Whisper fallback).
   - `$WHISPER_CPP_BIN` + `$WHISPER_MODEL` env vars (needed only for Whisper fallback).
3. For each URL, run:

   ```bash
   python .claude/skills/ingest/scripts/yt_fetch.py <url> --out-dir content/_raw/processed/
   ```

   On success, stdout is one-line JSON: `{video_id, title, archive_path, transcription, duration}`.
   On failure, exit code is 2 (bad URL) or 3 (fetch failure), with the reason on stderr. **Skip that URL and continue with the rest.** Collect failures for the final report.

4. Build a `Source` object per URL (in-memory, for Phase 1/2):

   ```
   Source { origin: "youtube", title, body=<archive file contents>, tokens (from title + chapters + first 2000 chars), meta (from frontmatter), raw_path=archive_path }
   ```

5. Inbox files (if any) also yield `Source` objects with `origin: "file"`. Phase 1 operates on the union.

**Idempotency check.** Before fetching, scan `content/_indexes/catalog.md` and the topic-folder notes for any frontmatter with the same `video_id`. If a match exists, skip Phase 0 fetch for that URL and feed the existing source path into Phase 2 as an overlap-merge candidate.

### Phase 1 — Pre-scan

1. Read `content/_indexes/vault-map.md` to understand current vault structure.
2. List `content/_raw/inbox/` AND merge in any `Source` objects built by Phase 0. If both are empty, report "Inbox empty and no URLs provided, nothing to process" and exit.
3. **Cluster detection.** For each pair of sources (file or YT):
   - Tokenize titles (or YT video titles): split on spaces, hyphens, underscores; lowercase; drop English/Polish stop-words.
   - Read the first ~200 characters of each source body (file content or transcript) for additional tokens. YT sources also contribute their channel name and chapter titles as tokens.
   - Group files sharing **≥2 distinctive tokens** OR one strong product-name token appearing in multiple titles.
   - A cluster requires **≥2 files** to form.
4. **If any clusters exist, send the user one consolidated message** containing all clusters. Format:

   ```
   Cluster "<name>" (<N> files):
     - <filename>   [parent candidate]   ← only if title lacks team/repo slash pattern but shares cluster tokens
     - <filename>   [repo]
     ...
   Options:
     A) Separate tool notes (CLAUDE.md default — each repo gets own note)
     B) Parent hub note + children (knowledge-note + N tool notes, bidirectional links)
     C) Custom — describe
   ```

   Wait for the user's choice per cluster before proceeding to Phase 2.

5. Files outside any cluster process autonomously in Phase 2 — no per-file prompt.

### Phase 2 — Execute

For each file or cluster (cluster handling per the user's choice from Phase 1):

6. Determine topic folder and note type per CLAUDE.md rules (sub-patterns: `BOOKS/`, `TOOLS/`, `KNOWLEDGE/INFO/`, `KNOWLEDGE/HOWTO/`, `NOTES/`, `HABITS/`). For YT-origin sources, classification input is `title + description + channel + chapter titles + first ~2000 chars of transcript`. YT-origin sources always use `type: knowledge-note` with template `templates/knowledge_note_info.md`.

   **Language enforcement:** The canonical vault language is **English** (see CLAUDE.md "Writing Style"). If the source content is in Polish or any other language, **translate it to English while ingesting**. This applies to: body prose, frontmatter `title` / `summary` / `tags`, and any quoted material. Preserve verbatim: proper nouns (vendor/product/person/place names), code blocks, URLs, dates, wikilinks, emoji. Polish proper nouns (e.g., place names like Bieszczady, vendor names like Pstryk) stay in Polish; their surrounding prose is translated.
7. Check `content/_indexes/catalog.md` for overlap with existing notes:
   - Overlap → merge into existing note, preserving all user-authored content.
   - No overlap → create from the appropriate template under `content/templates/` (per CLAUDE.md "Templates" table).
8. Fill frontmatter: `title`, `date` (today), `tags`, `type`, `source`, `agent-created: true`, `summary:` (one line).

   For YT-origin notes, `source` points at the archived transcript (e.g. `_raw/processed/2026-05-22_yt-<id>_<slug>.md`) and the following YT-specific fields are appended:

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
9. Add wikilinks to related notes; update those target notes to backlink.
10. **Move attachments.** Find image/media files referenced by the source (`.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webm`, `.pdf`, etc.) that landed in `content/` root or `content/_raw/inbox/`. Move them to `content/ATTACHMENTS/`. Update any `![[filename]]` references in the new note to point to the moved location.
11. Move source:
    - File sources: `content/_raw/inbox/<file>` → `content/_raw/processed/YYYY-MM-DD_<originalname>.<ext>`.
    - YT sources: archive file already lives in `content/_raw/processed/` from Phase 0 — verify the note's `source:` frontmatter matches the archive path; no move needed.
12. Update all three indexes per CLAUDE.md auto-update rules:
    - `catalog.md` — add or update the entry line in the correct folder section.
    - `vault-map.md` — increment folder count, refresh top-tags, prepend to Recent Changes.
    - `graph.md` — add outgoing links for the new note; update incoming-link entries on every target note.

Phase 2 is autonomous. No per-file confirmation. Cluster decisions were already made in Phase 1.

### Phase 3 — Final Checklist

13. Re-read `vault-map.md`:
    - Does `total_notes` match the delta (old count + new notes − merges)?
    - Are all new notes present in `Recent Changes`?
14. Spot-check `catalog.md` — every new note has an entry line in its folder section.
15. Print final report:

    ```
    Ingest complete.
    - Processed: X sources (F files, Y YouTube URLs)
    - Created:   N new notes
    - Merged:    M into existing notes
    - Attachments moved: W
    - YouTube:   captions=A, whisper=B, failed=C
    - Indexes:   ✅ vault-map / catalog / graph
    Failures (if any):
      - <url> — <reason>
    Inbox now empty.
    ```

If the checklist fails, surface the discrepancy and offer to fix before reporting completion.

## Failure Handling

| Failure | Behavior |
|---|---|
| Argument is non-empty but not a YT URL | Abort whole `/ingest` call before Phase 0; report bad arg. |
| `yt-dlp` not on PATH | Abort whole call with install hint. |
| Video unavailable / private / removed | Skip that URL, continue rest. Final report flags it. |
| No captions AND Whisper fallback fails | Skip that URL. Final report names which step failed. |
| Captions 429 / per-language failure | `yt_fetch.py` iterates languages individually with 15s back-off retry on HTTP 429, so a rate-limited or missing language no longer aborts the whole captions step. |
| Classification ambiguous | Best-guess folder + `#todo/classification` tag (existing fallback). |
| Network/timeout during fetch | `yt_fetch.py` returns non-zero; skill skips that URL. |
| Phase 0 succeeds, Phase 2 fails mid-note | Transcript archive already in `_raw/processed/`; rerun targets it for completion. |

## Prerequisites

- `yt-dlp` on PATH — required for any YT URL.
- `ffmpeg` on PATH — required only when captions are unavailable (Whisper fallback).
- `$WHISPER_CPP_BIN` + `$WHISPER_MODEL` env vars — required only for Whisper fallback. Default model: `ggml-large-v3.bin`.

## See also

CLAUDE.md "Navigation Protocol" — read on every operation before this workflow.
CLAUDE.md "Templates" table — for the type → template mapping used in step 7.
