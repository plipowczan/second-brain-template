"""Full rebuild of the three vault indexes from all notes under content/.

Deterministic: parses frontmatter + wikilinks from every .md note (excluding
_raw, _indexes, _outputs, _graveyard, templates, .obsidian) and regenerates
vault-map.md, catalog.md, graph.md per CLAUDE.md "Navigation Protocol".
"""
from __future__ import annotations

import os
import re
import datetime
from collections import Counter, defaultdict

import yaml

CONTENT = "content"
EXCLUDE = {"_raw", "_indexes", "_outputs", "_graveyard", "templates", ".obsidian"}
# Non-note markdown files at the content root (meta docs + unrendered templates).
EXCLUDE_FILES = {"WRITING_STYLE.md", "WRITING_STYLE_ANALYSIS.md", "_index.md"}
WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
NOW = datetime.datetime.now().replace(microsecond=0).isoformat() + "Z"


def rel(path: str) -> str:
    return os.path.relpath(path, CONTENT).replace("\\", "/")


def parse_frontmatter(text: str):
    """Return (meta_dict, body). meta is {} if no frontmatter."""
    if not text.startswith("---"):
        return {}, text
    # split: --- \n ... \n --- \n body
    parts = text.split("\n")
    if parts[0].strip() != "---":
        return {}, text
    end = None
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    fm_text = "\n".join(parts[1:end])
    body = "\n".join(parts[end + 1:])
    try:
        meta = yaml.safe_load(fm_text) or {}
        if not isinstance(meta, dict):
            meta = {}
    except yaml.YAMLError:
        meta = {}
    return meta, body


def first_summary_line(body: str) -> str:
    for line in body.split("\n"):
        s = line.strip()
        if not s:
            continue
        if s.startswith("#") or s.startswith("---") or s.startswith("```"):
            continue
        if s.startswith("Template:"):
            continue
        # strip markdown emphasis / wikilink brackets for readability
        s = re.sub(r"\[\[([^\]|]+)(\|[^\]]+)?\]\]", r"\1", s)
        s = s.lstrip("-*> ").strip()
        if s:
            return s
    return ""


def extract_links(body: str):
    """Ordered, de-duped wikilink targets (alias + header stripped)."""
    seen = []
    for m in WIKILINK.finditer(body):
        inner = m.group(1).replace("\\|", "|")  # Obsidian table-escaped pipe
        raw = inner.split("|")[0].split("#")[0].strip()
        if raw and raw not in seen:
            seen.append(raw)
    return seen


# ---- scan ----
notes = []  # list of dicts
for dirpath, dirnames, filenames in os.walk(CONTENT):
    parts = rel(dirpath).split("/")
    if any(p in EXCLUDE for p in parts):
        dirnames[:] = []
        continue
    for fn in filenames:
        if not fn.endswith(".md"):
            continue
        if fn.endswith(".template.md") or fn in EXCLUDE_FILES:
            continue
        full = os.path.join(dirpath, fn)
        with open(full, encoding="utf-8") as f:
            text = f.read()
        meta, body = parse_frontmatter(text)
        relpath = rel(full)
        relnoext = relpath[:-3]
        folder = os.path.dirname(relpath).replace("\\", "/")
        if folder == "":
            folder = "(root)"
        stem = os.path.basename(relnoext)
        title = meta.get("title") or stem
        if isinstance(title, str):
            title = title.strip()
        ntype = meta.get("type") or "untyped"
        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        tags = [str(t).strip() for t in tags if str(t).strip()]
        date = meta.get("date")
        date = str(date).strip() if date is not None else ""
        summary = meta.get("summary") or first_summary_line(body)
        summary = re.sub(r"\s+", " ", str(summary)).strip()
        notes.append({
            "relpath": relnoext, "folder": folder, "stem": stem,
            "title": title, "type": ntype, "tags": tags, "date": date,
            "summary": summary, "links": extract_links(body),
        })

notes.sort(key=lambda n: n["relpath"].lower())
path_set = {n["relpath"] for n in notes}
stem_map = {}
for n in notes:
    stem_map.setdefault(n["stem"], n["relpath"])


def resolve(raw: str) -> str:
    if raw in path_set:
        return raw
    stem = raw.split("/")[-1]
    if stem in stem_map:
        return stem_map[stem]
    return raw


# ---- graph ----
incoming = defaultdict(list)
outgoing = {}
edge_count = 0
for n in notes:
    outs = []
    for raw in n["links"]:
        tgt = resolve(raw)
        outs.append(tgt)
        edge_count += 1
        if tgt in path_set:
            incoming[tgt].append(n["relpath"])
    if outs:
        outgoing[n["relpath"]] = outs

graph_lines = [
    "---", f"updated: {NOW}", f"nodes: {len(notes)}", f"edges: {edge_count}",
    "---", "# Link Graph", "", "## Outgoing",
]
for src in sorted(outgoing, key=str.lower):
    graph_lines.append(f"{src} -> " + ", ".join(outgoing[src]))
graph_lines += ["", "## Incoming"]
for tgt in sorted(incoming, key=str.lower):
    srcs = sorted(set(incoming[tgt]), key=str.lower)
    graph_lines.append(f"{tgt} <- " + ", ".join(srcs))
with open(os.path.join(CONTENT, "_indexes", "graph.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(graph_lines) + "\n")


# ---- catalog ----
by_folder = defaultdict(list)
for n in notes:
    by_folder[n["folder"]].append(n)


def folder_sort_key(fld):
    return (fld != "(root)", fld.lower())


cat_lines = ["---", f"updated: {NOW}", f"entries: {len(notes)}", "---", "# Note Catalog"]
for fld in sorted(by_folder, key=folder_sort_key):
    cat_lines.append("")
    cat_lines.append(f"## {fld}")
    for n in sorted(by_folder[fld], key=lambda x: x["title"].lower()):
        tags = ", ".join(n["tags"])
        links = ", ".join(n["links"]) if n["links"] else "-"
        cat_lines.append(
            f"- **{n['title']}** | {n['type']} | {n['date']} | [{tags}] | {n['summary']} | → {links}"
        )
with open(os.path.join(CONTENT, "_indexes", "catalog.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(cat_lines) + "\n")


# ---- vault-map ----
tag_counter = Counter()
for n in notes:
    tag_counter.update(n["tags"])

vm = ["---", f"updated: {NOW}", f"total_notes: {len(notes)}", "---", "# Vault Map", "",
      "## Folders", "| folder | notes | types | top-tags |", "|--------|------:|-------|----------|"]
for fld in sorted(by_folder, key=folder_sort_key):
    fnotes = by_folder[fld]
    tcount = Counter(n["type"] for n in fnotes)
    types = ", ".join(f"{t}({c})" for t, c in tcount.most_common())
    ftags = Counter()
    for n in fnotes:
        ftags.update(n["tags"])
    top = ", ".join(t for t, _ in ftags.most_common(5))
    vm.append(f"| {fld} | {len(fnotes)} | {types} | {top} |")

vm += ["", "## Tag Cloud"]
cloud = " ".join(f"{t}:{tag_counter[t]}" for t in sorted(tag_counter, key=str.lower))
vm.append(cloud)

vm += ["", "## Recent Changes"]
dated = [n for n in notes if re.match(r"\d{4}-\d{2}-\d{2}", n["date"])]
dated.sort(key=lambda n: n["date"], reverse=True)
for n in dated[:15]:
    snip = n["summary"][:75]
    vm.append(f"- {n['date']} {n['relpath']} ({snip})")
with open(os.path.join(CONTENT, "_indexes", "vault-map.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(vm) + "\n")

print(f"OK notes={len(notes)} edges={edge_count} "
      f"incoming_targets={len(incoming)} tags={len(tag_counter)} dated={len(dated)}")
