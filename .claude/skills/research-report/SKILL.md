---
name: research-report
user-invocable: true
description: Summarize deep research results into markdown report, cover all fields, skip uncertain values.
allowed-tools: Read, Write, Glob, Bash, AskUserQuestion
---

# Research Report - Summary Report

## Trigger
`/research-report`

## Workflow

### Step 1: Locate Results Directory
Find `outline.yaml` in `content/_raw/research-workspaces/*/` (preferred) or anywhere via Glob fallback. Read topic and output_dir config.

### Step 2: Scan Optional Summary Fields
Read all JSON results, extract fields suitable for TOC display (numeric, short metrics), e.g.:
- github_stars
- google_scholar_cites
- swe_bench_score
- user_scale
- valuation
- release_date

Use AskUserQuestion to ask user:
- Which fields to display in TOC besides item name?
- Provide dynamic options list (based on actual fields in JSON)

### Step 3: Generate Python Conversion Script
Generate `generate_report.py` in `{topic}/` directory, script requirements:
- Read all JSON from output_dir
- Read fields.yaml to get field structure
- Cover all field values from each JSON
- Skip fields with values containing [uncertain]
- Skip fields listed in uncertain array
- Generate markdown report format: Table of contents (with anchor links + user-selected summary fields) + Detailed content (by field category)
- Save to `{topic}/report.md`

**TOC Format Requirements**:
- Must include every item
- Each item displays: number, name (anchor link), user-selected summary fields
- Example: `1. [GitHub Copilot](#github-copilot) - Stars: 10k | Score: 85%`

#### Script Technical Requirements (Must Follow)

**1. JSON Structure Compatibility**
Support two JSON structures:
- Flat structure: Fields directly at top level `{"name": "xxx", "release_date": "xxx"}`
- Nested structure: Fields in category sub-dict `{"basic_info": {"name": "xxx"}, "technical_features": {...}}`

Field lookup order: Top level -> category mapping key -> Traverse all nested dicts

**2. Category Multi-language Mapping**
fields.yaml category names and JSON keys can be any combination (CN-CN, CN-EN, EN-CN, EN-EN). Must establish bidirectional mapping:
```python
CATEGORY_MAPPING = {
    "Basic Info": ["basic_info", "Basic Info"],
    "Technical Features": ["technical_features", "technical_characteristics", "Technical Features"],
    "Performance Metrics": ["performance_metrics", "performance", "Performance Metrics"],
    "Milestone Significance": ["milestone_significance", "milestones", "Milestone Significance"],
    "Business Info": ["business_info", "commercial_info", "Business Info"],
    "Competition & Ecosystem": ["competition_ecosystem", "competition", "Competition & Ecosystem"],
    "History": ["history", "History"],
    "Market Positioning": ["market_positioning", "market", "Market Positioning"],
}
```

**3. Complex Value Formatting**
- list of dicts (e.g., key_events, funding_history): Format each dict as one line, separate kv with ` | `
- Normal list: Short lists joined with comma, long lists displayed with line breaks
- Nested dict: Recursive formatting, display with semicolon or line breaks
- Long text strings (over 100 chars): Add line breaks `<br>` or use blockquote format for readability

**4. Extra Fields Collection**
Collect fields that exist in JSON but not defined in fields.yaml, put in "Other Info" category. Note to filter:
- Internal fields: `_source_file`, `uncertain`
- Nested structure top-level keys: `basic_info`, `technical_features` etc.
- `uncertain` array: Display each field name on separate line, don't compress into one line

**5. Uncertain Value Skipping**
Skip conditions:
- Field value contains `[uncertain]` string
- Field name is in `uncertain` array
- Field value is None or empty string

### Step 4: Execute Script
Run `python content/_raw/research-workspaces/{topic_slug}/generate_report.py`

### Step 5: Promote Report to Brain Inbox

After `report.md` is generated in the workspace, create a brain-ready copy in `content/_raw/inbox/` so `/ingest` can classify it into the proper topic folder.

**Filename:** `content/_raw/inbox/{YYYY-MM-DD}-research-{topic_slug}.md` (current date in ISO format).

**Prepend Obsidian frontmatter** to the report contents:

```yaml
---
title: "{topic} — Research Report"
date: {YYYY-MM-DD}
enableToc: true
openToc: true
tags: ["research", "compiled"]   # add topic-derived tags if obvious from items/categories
type: compiled-note
source: "research-en deep research — content/_raw/research-workspaces/{topic_slug}/"
agent-created: true
summary: "{one-line description of what was researched, ~15 words}"
---

```

Then append the full markdown body from `report.md`.

**Note to user after writing:**
- Print the inbox path
- Suggest: "Run `/ingest` to classify this into the proper topic folder (likely `AI/`, `BUSINESS/`, etc.) and update indexes."
- Workspace files (`outline.yaml`, `fields.yaml`, `results/*.json`, `generate_report.py`, original `report.md`) stay in `content/_raw/research-workspaces/{topic_slug}/` for future `/research-add-items` or `/research-add-fields` runs.

## Output
- `content/_raw/research-workspaces/{topic_slug}/generate_report.py` — Conversion script
- `content/_raw/research-workspaces/{topic_slug}/report.md` — Raw summary report (workspace copy)
- `content/_raw/inbox/{YYYY-MM-DD}-research-{topic_slug}.md` — Brain-ingestible report with Obsidian frontmatter
