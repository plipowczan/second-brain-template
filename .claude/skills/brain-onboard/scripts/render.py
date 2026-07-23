#!/usr/bin/env python3
"""Render a brain template by substituting {{VAR}} placeholders and resolving
<!-- IF:flag --> ... <!-- /IF:flag --> conditional blocks from a values dict.

Run ONLY on the brain templates (CLAUDE.template.md, WRITING_STYLE.template.md,
AGENTS.template.md) — never on content/templates/*, which use Obsidian's own
{{title}} placeholders.

Usage:
  python render.py --template PATH --values VALUES.json --out PATH

Behaviour:
  - Conditional blocks are resolved FIRST: the inner text is kept iff the flag's
    value in the values dict is truthy; the markers are stripped either way.
    A block whose flag is missing from the values dict is an error.
  - Then every remaining {{KEY}} is replaced by str(values[KEY]); a {{KEY}} with
    no matching value is an error (we fail loud rather than ship a half-filled
    file). Because false blocks are removed first, {{vars}} that live only inside
    a dropped block never trigger this error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

VAR = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")


class RenderError(Exception):
    pass


def resolve_conditionals(text: str, values: dict) -> str:
    block = re.compile(r"<!-- IF:([A-Za-z_][A-Za-z0-9_]*) -->(.*?)<!-- /IF:\1 -->", re.DOTALL)

    def repl(m: "re.Match") -> str:
        flag = m.group(1)
        if flag not in values:
            raise RenderError(f"conditional flag not in values: {flag}")
        return m.group(2) if values[flag] else ""

    prev = None
    while prev != text:
        prev = text
        text = block.sub(repl, text)
    return text


def substitute(text: str, values: dict) -> str:
    missing = []

    def repl(m: "re.Match") -> str:
        key = m.group(1)
        if key not in values:
            missing.append(key)
            return m.group(0)
        return str(values[key])

    out = VAR.sub(repl, text)
    if missing:
        raise RenderError("missing values for: " + ", ".join(sorted(set(missing))))
    return out


def render(text: str, values: dict) -> str:
    return substitute(resolve_conditionals(text, values), values)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Render a brain template.")
    ap.add_argument("--template", required=True)
    ap.add_argument("--values", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    with open(args.template, encoding="utf-8") as f:
        text = f.read()
    with open(args.values, encoding="utf-8") as f:
        values = json.load(f)

    try:
        out = render(text, values)
    except RenderError as e:
        print(f"render error: {e}", file=sys.stderr)
        return 2

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"rendered {args.template} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
