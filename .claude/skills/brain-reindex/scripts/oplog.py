#!/usr/bin/env python3
"""The operation log of a base: content/_outputs/log.md, one table row per run of a
skill that wrote, moved or retired notes, so the record of what the agent did survives
without git. Skills write it only through this script, so the format cannot drift.

Usage (run from the vault root, or pass --root <vault root> before or after the command):
    python oplog.py append --op <name> [--count key=N]... [--note <path>]... [--at YYYY-MM-DDTHH:MM]
    python oplog.py read [--since YYYY-MM-DD] [--until YYYY-MM-DD]
    python oplog.py slug <text>

append  Adds one row and prints it:
            | YYYY-MM-DD HH:MM | <op> | key=N key=N | `path`, `path` and N more |
        The time is UTC (now, or --at for tests). <op> matches [a-z][a-z-]*. "What" is
        built only from --count key=N tokens (key [a-z_]+, N a non-negative integer),
        in the order given, or "-". Notes are the --note paths, "\\" written as "/",
        repeats dropped, at most 10 as code spans and then "and N more", or "-"; "|" is
        escaped as "\\|". A path that holds a backtick or a line break is refused. Every
        path segment holding a private term of content/_privacy.md or the git-ignored
        content/_privacy.local.md (matched by brain-export/scripts/privacy_sweep.py) is
        written as [private]. Without that script the row is written unmasked and one
        notice goes to stderr.
        A missing file is created with its header. Otherwise the file is only appended
        to: a final newline first when it lacks one, then the row as UTF-8 bytes with an
        LF ending, in one write. Nothing is ever rewritten, reordered or truncated.
read    Prints the rows as a JSON list sorted by time (a union merge can leave them out
        of order): {"time", "op", "counts": {key: N}, "notes": [path], "more": N}.
        --since and --until are inclusive UTC dates. The header, the separator and any
        line that is not a well-formed row are skipped. A missing file prints [].
slug    Prints a file-name-safe slug of a learning-session topic: lowercase, "ł" as "l"
        and other diacritics dropped, every run of other characters as "-", at most 60
        characters, "topic" when nothing is left, and "private" when the text or its
        slug holds a private term.

Exit codes: 0 done, 1 environment error (no content/ under the root, a file that cannot
be read or written), 2 refused input. Nothing is written on a non-zero exit.
"""

import argparse
import importlib.util
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

LOG = Path("content") / "_outputs" / "log.md"
# brain-export's privacy sweep, the one reader of the private terms. A module-level
# path so the tests can point it at a folder without the script.
PRIVACY_DIR = Path(__file__).resolve().parents[2] / "brain-export" / "scripts"
PRIVACY_SCRIPT = "privacy_sweep.py"
NOTICE = ("oplog: notice: brain-export/scripts/privacy_sweep.py could not be loaded, "
          "so private terms are not masked")

# Byte-identical in every base and every run, so a union merge of two clones that both
# created the file keeps one header.
HEADER = ("# Operation log\n"
          "\n"
          "| When (UTC) | Operation | What | Notes |\n"
          "|---|---|---|---|\n")
MAX_NOTES = 10
SLUG_MAX = 60
PRIVATE = "[private]"

OP_RE = re.compile(r"[a-z][a-z-]*")
COUNT_RE = re.compile(r"([a-z_]+)=([0-9]+)")
AT_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}")
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
TIME_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}")
CELL_SPLIT = re.compile(r"(?<!\\)\|")
NOTES_RE = re.compile(r"(`[^`]+`(?:, `[^`]+`)*)(?: and ([0-9]+) more)?")
SPAN_RE = re.compile(r"`([^`]+)`")


class Refused(Exception):
    """Input the log does not take: exit 2, nothing written."""


# --- Private terms

def load_privacy():
    """brain-export's privacy_sweep module, or None when it cannot be loaded. Loaded by
    file location on every call, with no sys.path or sys.modules entry, so a module of
    the same name elsewhere can never stand in for it."""
    path = Path(PRIVACY_DIR) / PRIVACY_SCRIPT
    try:
        spec = importlib.util.spec_from_file_location("_oplog_privacy_sweep", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception:  # missing, unreadable or broken: the caller says so
        return None
    if not all(callable(getattr(module, name, None)) for name in ("private_terms", "private_hit")):
        return None
    return module


def private_check(root):
    """A function text -> bool that says whether text holds a private term, or None when
    the privacy script cannot be loaded. A privacy file that exists but cannot be read
    raises (OSError, or ValueError for bad UTF-8): better no row than a leak."""
    module = load_privacy()
    if module is None:
        return None
    terms = module.private_terms(str(root))
    if not terms:
        return lambda text: False

    def check(text):
        # As written, in NFC (a file name from macOS comes decomposed, which the term as
        # written does not match) and folded (a name written without its diacritics).
        nfc = unicodedata.normalize("NFC", text)
        return any(module.private_hit(form, terms) for form in (text, nfc, fold(nfc)))
    return check


def mask_path(path, hit):
    """path with every segment that holds a private term written as [private]. A term
    that spans segments (one with a "/" in it) masks the whole path."""
    parts = path.split("/")
    masked = "/".join(PRIVATE if part and hit(part) else part for part in parts)
    return PRIVATE if hit(masked) else masked


# --- append

def parse_counts(tokens):
    counts = []
    for token in tokens:
        m = COUNT_RE.fullmatch(token)
        if not m:
            raise Refused(f"--count takes key=N only (key a-z and _, N a non-negative "
                          f"integer), not {token!r}")
        counts.append((m.group(1), int(m.group(2))))
    return counts


def parse_notes(raw_paths):
    notes = []
    for raw in raw_paths:
        if "`" in raw or "\n" in raw or "\r" in raw:
            raise Refused(f"a --note path cannot hold a backtick or a line break: {raw!r}")
        if not raw.strip():
            raise Refused("a --note path cannot be empty")
        try:
            raw.encode("utf-8")
        except UnicodeEncodeError:  # undecodable bytes in argv: no half-created file
            raise Refused(f"a --note path is not valid text: {raw!r}") from None
        path = unicodedata.normalize("NFC", raw.replace("\\", "/"))
        if path not in notes:
            notes.append(path)
    return notes


def parse_at(value):
    if value is None:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    try:
        if not AT_RE.fullmatch(value):
            raise ValueError
        return datetime.strptime(value, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M")
    except ValueError:
        raise Refused(f"--at takes a UTC time as YYYY-MM-DDTHH:MM, not {value!r}") from None


def build_row(when, op, counts, notes):
    what = " ".join(f"{key}={n}" for key, n in counts) or "-"
    shown = ["`" + p.replace("|", "\\|") + "`" for p in notes[:MAX_NOTES]]
    cell = ", ".join(shown) or "-"
    if len(notes) > MAX_NOTES:
        cell += f" and {len(notes) - MAX_NOTES} more"
    return f"| {when} | {op} | {what} | {cell} |\n"


def write_all(f, data):
    """One write call; a short write (never seen on a local disk) finishes the rest."""
    view = memoryview(data)
    while view:
        view = view[f.write(view):]


def append_row(log, row):
    """Create log with the header and row, or append row (after a newline the file
    lacks). Never rewrites what is there."""
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(log, "xb", buffering=0) as f:
            write_all(f, (HEADER + row).encode("utf-8"))
        return
    except FileExistsError:
        pass
    with open(log, "rb") as f:
        size = f.seek(0, 2)
        last = b""
        if size:
            f.seek(-1, 2)
            last = f.read(1)
    data = row.encode("utf-8")
    if size == 0:
        data = HEADER.encode("utf-8") + data
    elif last != b"\n":
        data = b"\n" + data
    with open(log, "ab", buffering=0) as f:
        write_all(f, data)


def cmd_append(args, root):
    if not OP_RE.fullmatch(args.op):
        raise Refused(f"--op takes a name of a-z and -, starting with a letter, not {args.op!r}")
    counts = parse_counts(args.count or [])
    notes = parse_notes(args.note or [])
    when = parse_at(args.at)
    hit = private_check(root)
    if hit is None:
        print(NOTICE, file=sys.stderr)
    else:
        notes = [mask_path(p, hit) for p in notes]
    row = build_row(when, args.op, counts, notes)
    append_row(root / LOG, row)
    print(row, end="")
    return 0


# --- read

def parse_row(line):
    """The row as a dict, or None for anything that is not a well-formed log row."""
    line = line.strip()
    cells = CELL_SPLIT.split(line)
    if len(cells) != 6 or cells[0].strip() or cells[-1].strip():
        return None
    when, op, what, notes_cell = (c.strip() for c in cells[1:5])
    if not TIME_RE.fullmatch(when):
        return None
    try:
        datetime.strptime(when, "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    if not OP_RE.fullmatch(op):
        return None
    counts = {}
    if what != "-":
        for token in what.split():
            m = COUNT_RE.fullmatch(token)
            if not m:
                return None
            counts[m.group(1)] = int(m.group(2))
    notes, more = [], 0
    if notes_cell != "-":
        m = NOTES_RE.fullmatch(notes_cell)
        if not m:
            return None
        notes = [p.replace("\\|", "|") for p in SPAN_RE.findall(m.group(1))]
        more = int(m.group(2) or 0)
    return {"time": when, "op": op, "counts": counts, "notes": notes, "more": more}


def read_rows(log):
    if not log.is_file():
        return []
    text = log.read_text(encoding="utf-8-sig", errors="replace")
    # split("\n"), not splitlines(): a path may hold U+2028 or another character that
    # splitlines() treats as a line break.
    rows = [r for r in (parse_row(line) for line in text.split("\n")) if r]
    return sorted(rows, key=lambda r: r["time"])


def parse_day(value, flag):
    try:
        if not DATE_RE.fullmatch(value):
            raise ValueError
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise Refused(f"{flag} takes a UTC date as YYYY-MM-DD, not {value!r}") from None
    return value


def cmd_read(args, root):
    since = parse_day(args.since, "--since") if args.since else None
    until = parse_day(args.until, "--until") if args.until else None
    rows = [r for r in read_rows(root / LOG)
            if (since is None or r["time"][:10] >= since)
            and (until is None or r["time"][:10] <= until)]
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


# --- slug

def fold(text):
    """text without diacritics: ł → l, then NFKD with the combining marks dropped."""
    text = unicodedata.normalize("NFKD", text.replace("ł", "l").replace("Ł", "L"))
    return "".join(c for c in text if not unicodedata.combining(c))


def slugify(text):
    s = fold(fold(text).lower())  # lower() can bring a combining mark back ("İ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:SLUG_MAX].rstrip("-") or "topic"


def cmd_slug(args, root):
    text = " ".join(args.text)
    slug = slugify(text)
    hit = private_check(root)
    if hit is None:
        print(NOTICE, file=sys.stderr)
    elif hit(text) or hit(slug):
        slug = "private"
    print(slug)
    return 0


# --- CLI

def build_parser():
    parser = argparse.ArgumentParser(
        prog="oplog.py", allow_abbrev=False,
        description="Append to and read the operation log content/_outputs/log.md.")
    root_help = "the vault root, the folder that holds content/ (default: the current folder)"
    parser.add_argument("--root", default=".", help=root_help)
    sub = parser.add_subparsers(dest="command", metavar="{append,read,slug}")
    sub.required = True

    a = sub.add_parser("append", allow_abbrev=False, help="append one row")
    a.add_argument("--op", required=True, help="the operation, [a-z][a-z-]*")
    a.add_argument("--count", action="append", metavar="KEY=N",
                   help="a count, key [a-z_]+ and N a non-negative integer; repeatable")
    a.add_argument("--note", action="append", metavar="PATH",
                   help="a path the run wrote, moved, archived or used; repeatable")
    a.add_argument("--at", metavar="YYYY-MM-DDTHH:MM", help="the UTC time (default: now)")
    a.set_defaults(run=cmd_append)

    r = sub.add_parser("read", allow_abbrev=False, help="print the rows as JSON")
    r.add_argument("--since", metavar="YYYY-MM-DD", help="first UTC date, inclusive")
    r.add_argument("--until", metavar="YYYY-MM-DD", help="last UTC date, inclusive")
    r.set_defaults(run=cmd_read)

    s = sub.add_parser("slug", allow_abbrev=False, help="print a topic slug")
    s.add_argument("text", nargs="+", help="the topic")
    s.set_defaults(run=cmd_slug)

    for p in (a, r, s):
        # SUPPRESS keeps a --root given before the command when none follows it.
        p.add_argument("--root", default=argparse.SUPPRESS, help=root_help)
        p.set_defaults(parser=p)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    root = Path(args.root)
    try:
        if not (root / "content").is_dir():
            print(f"oplog: error: no content/ under {root}: run from the vault root or "
                  f"pass --root", file=sys.stderr)
            return 1
        return args.run(args, root)
    except Refused as e:
        args.parser.error(str(e))  # exit 2 with the usage of the command
    except (OSError, ValueError) as e:
        print(f"oplog: error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
