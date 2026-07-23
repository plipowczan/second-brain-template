#!/usr/bin/env python3
"""Vault health scanner. Walks content/ topic folders, parses frontmatter, reports
issues. If a schema.yml is present in the working directory, the allowed types are
its keys and each type's `required` fields are enforced (schema_violation)."""
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
    for line in fm_raw.splitlines():
        item = re.match(r'^\s+-\s+(.*)$', line)
        if item and last_key is not None:
            # block-style YAML list item (e.g. `tags:` followed by `  - book`)
            cur = fm.get(last_key, "")
            if not isinstance(cur, list):
                cur = [] if cur in ("", None) else [cur]
                fm[last_key] = cur
            cur.append(item.group(1).strip())
            continue
        m = re.match(r'^([A-Za-z0-9_-]+):\s*(.*)$', line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
            last_key = m.group(1)
        else:
            last_key = None
    return fm, body


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
            path = os.path.join(dirpath, fn)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            fm, body = parse_fm(text)
            notes.append({"path": path.replace("\\", "/"), "name": fn[:-3], "fm": fm or {},
                          "body": body, "has_fm": fm is not None, "raw": text})

    keys = ["missing_frontmatter", "missing_title", "missing_date", "missing_tags",
            "missing_type", "missing_summary", "bad_type", "stub", "todo", "stale",
            "title_filename_mismatch", "schema_violation"]
    issues = {k: [] for k in keys}

    for n in notes:
        fm, p, body = n["fm"], n["path"], n["body"]
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

    return {"total": len(notes), "issues": issues,
            "counts": {k: len(v) for k, v in issues.items()}}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # avoid cp1252 crash on non-Latin content
    result = scan(ROOT, load_schema())
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
