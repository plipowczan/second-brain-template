#!/usr/bin/env python3
"""Vault health scanner. Walks content/ topic folders, parses frontmatter, reports
issues. If a schema.yml is present in the working directory, the allowed types are
its keys and each type's `required` fields are enforced (schema_violation).

The classes named in WARNINGS (also printed as the report's `warnings` list) are
advisory: a `_raw/` source path that does not exist, and contradiction callouts left
for the owner to resolve. They never block a commit."""
import os
import re
import sys
import json
from datetime import date

ROOT = "content"
EXCLUDE_TOP = {"_raw", "_indexes", "_outputs", "_graveyard", "templates", "ATTACHMENTS", ".obsidian"}
# Non-note markdown files at the content root (meta docs + unrendered templates).
EXCLUDE_FILES = {"WRITING_STYLE.md", "WRITING_STYLE_ANALYSIS.md", "_index.md"}
DEFAULT_TYPES = {"basic-note", "book-note", "knowledge-note", "tool",
                 "compiled-note", "answer-note", "quote", "quote-note", "dailyjournal"}
TODAY = date.today()
WARNINGS = ["missing_source_file", "contradiction"]
CONTRADICTION = re.compile(r'^\s*>\s*\[!contradiction\]', re.I)
FENCE = re.compile(r'^\s*(`{3,}|~{3,})(.*)$')
KEY = re.compile(r'^([A-Za-z0-9_-]+):\s*(.*)$')


def parse_fm(text):
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    fm_raw = text[3:end].strip()
    body = text[end + 4:]
    fm = {}
    last_key = None
    lines = fm_raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            # YAML ignores blank and comment lines, so they do not end a block list. After
            # a scalar value they end the key as before, so no scalar turns into a list.
            cur = fm.get(last_key) if last_key is not None else None
            if not (isinstance(cur, list) or (cur is not None and not _strip_comment(cur))):
                last_key = None
            continue
        item = re.match(r'^(\s*)-\s+(.*)$', line)
        if item and last_key is not None:
            cur = fm.get(last_key, "")
            # Block-style YAML list item: `tags:` followed by `  - book`, or by `- book`
            # without indentation (valid YAML, and what PyYAML's dump writes). An
            # unindented item belongs to the key only when that key has no value yet.
            if item.group(1) or isinstance(cur, list) or not _strip_comment(cur):
                if not isinstance(cur, list):
                    cur = [] if not _strip_comment(cur or "") else [cur]
                    fm[last_key] = cur
                cur.append(item.group(2).strip())
                continue
        m = KEY.match(line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
            last_key = m.group(1)
            joined, used = _flow_continuation(m.group(2), lines[i:])
            if used:
                fm[m.group(1)] = joined
                i += used
        else:
            last_key = None
    return fm, body


def _flow_continuation(value, rest):
    """A flow list that spans lines (`sources: [` ... `]`): return the list joined onto
    one line, comments removed, and the number of following lines it took. Return
    (None, 0) when the value opens no list, or when the list does not close before the
    next unindented key, so a stray `[` never swallows the keys after it."""
    parts = [_strip_comment(value)]
    if not parts[0].startswith("[") or _flow_depth(parts[0]) <= 0:
        return None, 0
    for n, line in enumerate(rest, 1):
        if re.match(r'^[A-Za-z0-9_-]+:(\s|$)', line):
            return None, 0
        parts.append(_strip_comment(line))
        joined = " ".join(p for p in parts if p)
        if _flow_depth(joined) <= 0:
            return joined, n
    return None, 0


def _flow_depth(raw):
    """Open `[` minus closing `]`, outside quoted strings."""
    depth = 0
    for _, ch in _unquoted(raw):
        depth += (ch == "[") - (ch == "]")
    return depth


def get_date(fm):
    d = fm.get("date", "").strip().strip('"')
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', d)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def load_schema(path="schema.yml"):
    """Return {type: {required: [...]}} from schema.yml, or {} if absent/unloadable."""
    try:
        import yaml
    except ImportError:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    return data.get("types", {}) or {}


def schema_violations(fm, ntype, schema):
    """List required fields missing/empty for this note's type; [] if type unknown."""
    spec = schema.get(ntype)
    if not spec:
        return []
    return [field for field in spec.get("required", []) if not fm.get(field)]


def _unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        return inner.replace("''", "'") if value[0] == "'" else inner
    return value


def _unquoted(raw):
    """Yield (index, char) for each character of a YAML scalar or flow list that is not
    inside a quoted string. A quote opens a string only where a scalar starts (at the
    beginning, or after `[` or `,`), so the apostrophe in `Bob's call` stays literal."""
    quote, at_start, i = None, True, 0
    while i < len(raw):
        ch = raw[i]
        if quote:
            if quote == '"' and ch == "\\":
                i += 2
                continue
            if ch == quote:
                if quote == "'" and raw[i + 1:i + 2] == "'":
                    i += 2
                    continue
                quote = None
        elif at_start and ch in "\"'":
            quote, at_start = ch, False
        else:
            yield i, ch
            if ch in "[,":
                at_start = True
            elif not ch.isspace():
                at_start = False
        i += 1


def _strip_comment(raw):
    """Drop a trailing YAML comment: a `#` at the start or after whitespace, outside a
    quoted string. `https://x.io/a#b` keeps its fragment."""
    for i, ch in _unquoted(raw):
        if ch == "#" and (i == 0 or raw[i - 1].isspace()):
            return raw[:i].strip()
    return raw.strip()


def _flow_items(raw):
    """Items of a flow-style YAML list (`["a", "b"]`); a plain scalar is one item."""
    raw = raw.strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        return [raw]
    inner = raw[1:-1]
    items, last = [], 0
    for i, ch in _unquoted(inner):
        if ch == ",":
            items.append(inner[last:i])
            last = i + 1
    items.append(inner[last:])
    return [i.strip() for i in items if i.strip()]


def source_values(fm):
    """Values of `source` and `sources`, written as a scalar, a block list or a flow list,
    with trailing YAML comments removed."""
    out = []
    for key in ("source", "sources"):
        val = fm.get(key)
        if not val:
            continue
        if isinstance(val, list):
            items = [_strip_comment(i) for i in val]
        else:
            items = _flow_items(_strip_comment(val))
        out.extend(v for v in (_unquote(i) for i in items) if v)
    return out


def missing_sources(fm, root, processed_cache):
    """One detail string per `_raw/` source path that does not exist under root. URLs,
    wikilinks and free-text sources are not paths and are skipped. For a missing
    `_raw/inbox/<name>`, archived copies `_raw/processed/*_<name>` are offered as the fix,
    together with `*_<stem>-<n>.<ext>`, the name ingest gives an archive whose name is
    taken: such a file means a second `<name>` went through the inbox."""
    out = []
    for value in source_values(fm):
        norm = value.replace("\\", "/")
        prefix = "content/" if norm.startswith("content/") else ""
        rel = norm[len(prefix):]
        if not rel.startswith("_raw/"):
            continue
        if os.path.exists(os.path.join(root, *rel.split("/"))):
            continue
        detail = f"source={value}"
        if rel.startswith("_raw/inbox/"):
            if "names" not in processed_cache:
                proc = os.path.join(root, "_raw", "processed")
                processed_cache["names"] = sorted(
                    f for f in os.listdir(proc)
                    if os.path.isfile(os.path.join(proc, f))) if os.path.isdir(proc) else []
            name = rel.rsplit("/", 1)[1]
            stem, ext = os.path.splitext(name)
            copy = re.compile(r'_' + re.escape(stem) + r'(-\d+)?' + re.escape(ext) + r'$')
            found = [f"{prefix}_raw/processed/{f}" for f in processed_cache["names"]
                     if copy.search(f)]
            if len(found) == 1:
                detail += f", fix={found[0]}"
            elif found:
                detail += ", candidates=" + "|".join(found)
        out.append(detail)
    return out


def contradiction_count(body):
    """Number of `> [!contradiction]` callouts, ignoring fenced code blocks. As in
    CommonMark, a fence closes only on a line of the same character, at least as long as
    the opening run and with nothing after it, so a ```` block can show ``` examples."""
    count, fence = 0, None
    for line in body.splitlines():
        m = FENCE.match(line)
        if fence is None:
            if m:
                fence = m.group(1)
                continue
            if CONTRADICTION.match(line):
                count += 1
        elif (m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence)
              and not m.group(2).strip()):
            fence = None
    return count


def scan(root=ROOT, schema=None):
    schema = schema or {}
    allowed = set(schema) if schema else set(DEFAULT_TYPES)
    notes = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        if rel != ".":
            top = rel.split(os.sep)[0]
            if top in EXCLUDE_TOP or top.startswith("."):
                dirnames[:] = []
                continue
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            if fn.endswith(".template.md") or fn in EXCLUDE_FILES:
                continue
            # Underscore prefix means infrastructure, not a note -- the same rule that
            # skips _raw/, _indexes/ etc. above, and the one build_indexes.py applies
            # to loose files, so a config file like content/_privacy.md is not linted
            # as a note without frontmatter.
            if fn.startswith("_"):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            fm, body = parse_fm(text)
            notes.append({"path": path.replace("\\", "/"), "name": fn[:-3], "fm": fm or {},
                          "body": body, "has_fm": fm is not None, "raw": text})

    keys = ["missing_frontmatter", "missing_title", "missing_date", "missing_tags",
            "missing_type", "missing_summary", "bad_type", "stub", "todo", "stale",
            "title_filename_mismatch", "schema_violation"] + WARNINGS
    issues = {k: [] for k in keys}
    processed_cache = {}

    for n in notes:
        fm, p, body = n["fm"], n["path"], n["body"]
        markers = contradiction_count(body)
        if markers:
            issues["contradiction"].append(
                f"{p} ({markers} marker{'' if markers == 1 else 's'})")
        if not n["has_fm"]:
            issues["missing_frontmatter"].append(p)
            continue
        if not fm.get("title"):
            issues["missing_title"].append(p)
        if not fm.get("date"):
            issues["missing_date"].append(p)
        if not fm.get("tags") or fm.get("tags") in ("[]", "[ ]"):
            issues["missing_tags"].append(p)
        t = fm.get("type", "")
        if not t:
            issues["missing_type"].append(p)
        elif t not in allowed:
            issues["bad_type"].append(f"{p} (type={t})")
        if not fm.get("summary"):
            issues["missing_summary"].append(p)
        clean = re.sub(r'^#.*$', '', body, flags=re.M)
        clean = re.sub(r'Template:.*$', '', clean, flags=re.M)
        clean = re.sub(r'#todo\S*', '', clean)
        if len(clean.strip()) < 200:
            issues["stub"].append(f"{p} ({len(clean.strip())} chars)")
        todos = re.findall(r'#todo\S*', n["raw"])
        if todos:
            issues["todo"].append(f"{p} ({', '.join(sorted(set(todos)))})")
        d = get_date(fm)
        rev = fm.get("agent-reviewed", "").strip().strip('"')
        revd = None
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})', rev)
        if m:
            revd = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d and (TODAY - d).days > 365:
            if not revd or (TODAY - revd).days > 365:
                issues["stale"].append(f"{p} (date={d})")
        ftitle = fm.get("title", "").strip().strip('"')
        if ftitle and ftitle != n["name"]:
            issues["title_filename_mismatch"].append(f'{p} (title="{ftitle}")')
        if schema and t:
            missing = schema_violations(fm, t, schema)
            if missing:
                issues["schema_violation"].append(f"{p} (type={t} missing={','.join(missing)})")
        for detail in missing_sources(fm, root, processed_cache):
            issues["missing_source_file"].append(f"{p} ({detail})")

    return {"total": len(notes), "issues": issues,
            "counts": {k: len(v) for k, v in issues.items()},
            "warnings": list(WARNINGS)}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # avoid cp1252 crash on non-Latin content
    result = scan(ROOT, load_schema())
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
