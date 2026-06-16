"""YouTube source fetcher for /ingest skill.

Fetches metadata + transcript for a YouTube URL and writes a synthesized
source markdown file under content/_raw/processed/ for downstream ingest.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs


class YTUrlError(ValueError):
    """Raised when input does not look like a recognized YouTube URL."""


_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def normalize_url(url: str) -> str:
    """Return canonical 11-char video_id for a YouTube URL.

    Raises YTUrlError on anything that doesn't parse to a valid YT video id.
    """
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or parsed.netloc not in _HOSTS:
        raise YTUrlError(f"Not a YouTube URL: {url!r}")

    if parsed.netloc == "youtu.be":
        candidate = parsed.path.strip("/")
    else:
        candidate = parse_qs(parsed.query).get("v", [""])[0]

    if not _VIDEO_ID_RE.match(candidate):
        raise YTUrlError(f"Could not extract video_id from {url!r}")
    return candidate


from dataclasses import dataclass


@dataclass(frozen=True)
class VttCue:
    start: float  # seconds
    text: str


_VTT_TIME_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->")
_VTT_TAG_RE = re.compile(r"<[^>]+>")


def _vtt_time_to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_vtt(vtt_text: str) -> list[VttCue]:
    """Parse WebVTT into a list of cues. Strips styling tags and timing tags.

    Coalesces consecutive identical-text cues (YouTube auto-captions emit many).
    """
    cues: list[VttCue] = []
    lines = vtt_text.splitlines()
    i = 0
    while i < len(lines):
        m = _VTT_TIME_RE.match(lines[i])
        if not m:
            i += 1
            continue
        start = _vtt_time_to_seconds(*m.groups())
        i += 1
        text_parts: list[str] = []
        while i < len(lines) and lines[i].strip():
            text_parts.append(_VTT_TAG_RE.sub("", lines[i]).strip())
            i += 1
        text = " ".join(p for p in text_parts if p)
        if text and (not cues or cues[-1].text != text):
            cues.append(VttCue(start=start, text=text))
    return cues


def format_timestamp(seconds: float) -> str:
    """Format seconds as M:SS or H:MM:SS."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


import unicodedata


_TRANSLITERATE = str.maketrans(
    "ÀÁÂÃÄÅàáâãäåÆæÇçÈÉÊËèéêëÌÍÎÏìíîïÐðÑñÒÓÔÕÖØòóôõöøÙÚÛÜùúûüÝýÿŁłŃńŚśŹźŻż",
    "AAAAAAaaaaaaAaCcEEEEeeeeIIIIiiiiDdNnOOOOOOooooooUUUUuuuuYyyLlNnSsZzZz",
)


def slugify(text: str, max_len: int = 60) -> str:
    """ASCII slug: lowercase, hyphenated, max_len chars."""
    text = text.translate(_TRANSLITERATE)
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug


def archive_filename(date_str: str, video_id: str, title: str) -> str:
    """Return the canonical archive filename for a YT source."""
    return f"{date_str}_yt-{video_id}_{slugify(title)}.md"


import json
import shutil
import subprocess
import tempfile
import os
from pathlib import Path


class YTFetchError(RuntimeError):
    """Raised when yt-dlp or whisper fails in a way we should report."""


def yt_dlp_available() -> bool:
    return shutil.which("yt-dlp") is not None


def fetch_metadata(url: str, timeout: int = 60) -> dict:
    """Run yt-dlp to get full video metadata as a dict."""
    if not yt_dlp_available():
        raise YTFetchError("yt-dlp not on PATH")
    try:
        proc = subprocess.run(
            ["yt-dlp", "--dump-single-json", "--skip-download", "--no-warnings", url],
            capture_output=True, text=True, timeout=timeout, check=True,
        )
    except subprocess.CalledProcessError as e:
        raise YTFetchError(f"yt-dlp metadata failed: {e.stderr.strip()[:500]}") from e
    except subprocess.TimeoutExpired as e:
        raise YTFetchError(f"yt-dlp metadata timed out after {timeout}s") from e
    data = json.loads(proc.stdout)
    # Normalize: ensure `video_id` key exists
    data["video_id"] = data.get("id", "")
    return data


import time


_DEFAULT_LANGS = ("en", "en-US", "en-GB", "pl")


def _try_one_lang(url: str, lang: str, out_template: str, timeout: int, retries: int = 2) -> bool:
    """Try to fetch subs for a single language. Returns True on success, False on hard failure.

    Retries on HTTP 429 with short backoff; treats "no subs for this lang" as a soft miss (False).
    """
    for attempt in range(retries + 1):
        try:
            subprocess.run(
                [
                    "yt-dlp", "--write-subs", "--write-auto-subs",
                    "--sub-langs", lang, "--sub-format", "vtt",
                    "--skip-download", "--no-warnings",
                    "-o", out_template, url,
                ],
                capture_output=True, text=True, timeout=timeout, check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            err = (e.stderr or "").strip()
            if "429" in err and attempt < retries:
                time.sleep(15 * (attempt + 1))
                continue
            # 429 exhausted, or any other yt-dlp error for this language: treat as miss.
            return False
        except subprocess.TimeoutExpired:
            return False
    return False


def fetch_captions_vtt(url: str, langs: str | tuple[str, ...] = _DEFAULT_LANGS, timeout: int = 120) -> str | None:
    """Download caption VTT for the URL. Returns VTT text or None if no captions available.

    Iterates per-language so a 429 / missing-subs on one language does not abort the rest.
    Accepts either a comma-separated string (legacy) or a sequence of language codes.
    """
    if not yt_dlp_available():
        raise YTFetchError("yt-dlp not on PATH")
    if isinstance(langs, str):
        lang_list = [x.strip() for x in langs.split(",") if x.strip()]
    else:
        lang_list = list(langs)

    with tempfile.TemporaryDirectory() as tmp:
        out_template = os.path.join(tmp, "sub")
        for lang in lang_list:
            if _try_one_lang(url, lang, out_template, timeout):
                break  # stop at the first language that yields anything

        vtt_files = sorted(Path(tmp).glob("*.vtt"))
        if not vtt_files:
            return None
        # Prefer non-auto captions if both exist (no "auto" tag in filename).
        manual = [p for p in vtt_files if ".auto." not in p.name]
        chosen = manual[0] if manual else vtt_files[0]
        return chosen.read_text(encoding="utf-8")


def _yaml_str(s: str) -> str:
    """Quote string for safe YAML inclusion."""
    return json.dumps(s, ensure_ascii=False)


def _yaml_list(items: list) -> str:
    return "[" + ", ".join(_yaml_str(str(x)) for x in items) + "]"


def assemble_source_markdown(
    *,
    meta: dict,
    cues: list[VttCue],
    transcription: str,
    fetched_iso: str,
) -> str:
    """Build the full archived-source markdown (frontmatter + body)."""
    upload = meta["upload_date"]  # YYYYMMDD
    published = f"{upload[0:4]}-{upload[4:6]}-{upload[6:8]}"
    duration = int(meta["duration"])
    duration_human = format_timestamp(duration)

    chapter_lines = []
    for ch in meta.get("chapters") or []:
        title = ch.get("title", "")
        start = int(ch.get("start_time", 0))
        chapter_lines.append(f'  - {{ start: {start}, title: {_yaml_str(title)} }}')
    chapters_block = "chapters:\n" + ("\n".join(chapter_lines) if chapter_lines else "  []")

    fm = [
        "---",
        f"video_id: {meta['video_id']}",
        f"source_url: {meta['webpage_url']}",
        f"title: {_yaml_str(meta['title'])}",
        f"channel: {_yaml_str(meta['channel'])}",
        f"uploader_id: {_yaml_str(meta.get('uploader_id', ''))}",
        f"duration: {duration}",
        f"duration_human: {_yaml_str(duration_human)}",
        f"published: {published}",
        f"language: {meta.get('language') or 'unknown'}",
        f"transcription: {transcription}",
        chapters_block,
        f"tags: {_yaml_list(meta.get('tags') or [])}",
        f"categories: {_yaml_list(meta.get('categories') or [])}",
        f"fetched: {fetched_iso}",
        "---",
        "",
        f"# {meta['title']}",
        "",
    ]
    body_lines = [f"[{format_timestamp(c.start)}] {c.text}" for c in cues]
    return "\n".join(fm + body_lines) + ("\n" if body_lines else "")


_WHISPER_LINE_RE = re.compile(
    r"^\[(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}\]\s*(.*)$"
)


def whisper_available() -> bool:
    bin_path = os.environ.get("WHISPER_CPP_BIN")
    model_path = os.environ.get("WHISPER_MODEL")
    return bool(bin_path and model_path and Path(bin_path).exists() and Path(model_path).exists())


def parse_whisper_output(text: str) -> list[VttCue]:
    """Parse whisper.cpp default stdout format into cues."""
    cues: list[VttCue] = []
    for line in text.splitlines():
        m = _WHISPER_LINE_RE.match(line)
        if not m:
            continue
        h, mm, s, ms, body = m.groups()
        start = _vtt_time_to_seconds(h, mm, s, ms)
        body = body.strip()
        if body:
            cues.append(VttCue(start=start, text=body))
    return cues


def transcribe_with_whisper(url: str, timeout: int = 1800) -> list[VttCue]:
    """Download audio with yt-dlp and transcribe with whisper.cpp. Returns cues.

    Requires WHISPER_CPP_BIN and WHISPER_MODEL env vars and ffmpeg on PATH.
    """
    if not yt_dlp_available():
        raise YTFetchError("yt-dlp not on PATH")
    if not shutil.which("ffmpeg"):
        raise YTFetchError("ffmpeg not on PATH (required for audio extraction)")
    bin_path = os.environ.get("WHISPER_CPP_BIN")
    model_path = os.environ.get("WHISPER_MODEL")
    if not (bin_path and model_path):
        raise YTFetchError("WHISPER_CPP_BIN and WHISPER_MODEL env vars not set")
    if not Path(bin_path).exists():
        raise YTFetchError(f"WHISPER_CPP_BIN not found: {bin_path}")
    if not Path(model_path).exists():
        raise YTFetchError(f"WHISPER_MODEL not found: {model_path}")

    with tempfile.TemporaryDirectory() as tmp:
        audio = os.path.join(tmp, "audio.wav")
        try:
            subprocess.run(
                [
                    "yt-dlp", "-x", "--audio-format", "wav",
                    "--no-warnings",
                    "-o", os.path.join(tmp, "audio.%(ext)s"),
                    url,
                ],
                capture_output=True, text=True, timeout=timeout, check=True,
            )
        except subprocess.CalledProcessError as e:
            raise YTFetchError(f"yt-dlp audio failed: {e.stderr.strip()[:500]}") from e

        if not Path(audio).exists():
            raise YTFetchError("yt-dlp produced no audio.wav")

        try:
            proc = subprocess.run(
                [bin_path, "-m", model_path, "-f", audio, "-otxt", "-of", os.path.join(tmp, "out")],
                capture_output=True, text=True, timeout=timeout, check=True,
            )
        except subprocess.CalledProcessError as e:
            raise YTFetchError(f"whisper.cpp failed: {e.stderr.strip()[:500]}") from e

        # whisper.cpp -otxt writes <of>.txt with [HH:MM:SS.mmm --> HH:MM:SS.mmm]  text
        txt = Path(os.path.join(tmp, "out.txt"))
        if not txt.exists():
            # some whisper.cpp versions print to stdout
            return parse_whisper_output(proc.stdout)
        return parse_whisper_output(txt.read_text(encoding="utf-8"))


import datetime
import sys
import argparse


@dataclass(frozen=True)
class FetchResult:
    video_id: str
    title: str
    archive_path: Path
    transcription: str  # "captions" | "whisper-large-v3"
    duration: int


def fetch_to_archive(
    *,
    meta: dict,
    cues: list[VttCue],
    transcription: str,
    out_dir: Path,
    today: datetime.date,
    fetched_iso: str,
) -> FetchResult:
    """Write the archived source file. Pure I/O — no network."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = archive_filename(today.isoformat(), meta["video_id"], meta["title"])
    target = out_dir / fname
    content = assemble_source_markdown(
        meta=meta, cues=cues, transcription=transcription, fetched_iso=fetched_iso,
    )
    target.write_text(content, encoding="utf-8")
    return FetchResult(
        video_id=meta["video_id"],
        title=meta["title"],
        archive_path=target,
        transcription=transcription,
        duration=int(meta["duration"]),
    )


def process_url(url: str, out_dir: Path) -> FetchResult:
    """End-to-end: URL → archived source file. Raises YTFetchError on failure."""
    video_id = normalize_url(url)
    meta = fetch_metadata(url)
    meta["video_id"] = video_id

    vtt = fetch_captions_vtt(url)
    if vtt:
        cues = parse_vtt(vtt)
        transcription = "captions"
    else:
        if not whisper_available():
            raise YTFetchError(
                "No captions and whisper.cpp not configured "
                "(set WHISPER_CPP_BIN and WHISPER_MODEL, install ffmpeg)"
            )
        cues = transcribe_with_whisper(url)
        transcription = "whisper-large-v3"

    if not cues:
        raise YTFetchError("Transcript fetch returned no content")

    return fetch_to_archive(
        meta=meta, cues=cues, transcription=transcription,
        out_dir=out_dir,
        today=datetime.date.today(),
        fetched_iso=datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch a YouTube video as a wiki source.")
    parser.add_argument("url", help="YouTube URL")
    parser.add_argument(
        "--out-dir", required=True, type=Path,
        help="Directory to write the archived source (e.g. content/_raw/processed/)",
    )
    args = parser.parse_args(argv)

    try:
        result = process_url(args.url, args.out_dir)
    except YTUrlError as e:
        print(f"ERROR url: {e}", file=sys.stderr)
        return 2
    except YTFetchError as e:
        print(f"ERROR fetch: {e}", file=sys.stderr)
        return 3

    print(json.dumps({
        "video_id": result.video_id,
        "title": result.title,
        "archive_path": str(result.archive_path),
        "transcription": result.transcription,
        "duration": result.duration,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
