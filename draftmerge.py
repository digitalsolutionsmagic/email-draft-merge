#!/usr/bin/env python3
"""email-draft-merge: turn a CSV and a text template into email DRAFTS.

Standard library only. Works offline. It never sends anything. A draft is only
produced when every {{placeholder}} in the template has a value in that lead's
row, so nothing is invented.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections import Counter
from pathlib import Path

__version__ = "0.1.0"


class MergeError(Exception):
    """A problem the user can fix (bad path, bad template, missing column...)."""


PLACEHOLDER_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
EMAIL_RE = re.compile(
    r"^[^@\s<>]+@([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$"
)
EMAIL_NAMES = {"email", "e mail", "email address", "work email", "e mail address"}
OUT_COLS = ["row", "to", "subject", "body", "status", "reason"]


def norm(value) -> str:
    return re.sub(r"[\s_\-]+", " ", (value or "").strip().lower())


def parse_template(text: str):
    """Return (subject, body). The first non-empty line must be 'Subject: ...'."""
    lines = text.lstrip("﻿").splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines or not lines[0].lower().startswith("subject:"):
        raise MergeError("the template must start with a line like 'Subject: ...'")
    subject = lines[0][len("subject:"):].strip()
    if not subject:
        raise MergeError("the Subject line is empty")
    body = "\n".join(lines[1:]).strip("\n")
    return subject, body


def render(text: str, values: dict):
    """Fill {{placeholders}} from values (keys already normalized).

    Returns (rendered_text, missing_names). A placeholder with an empty or
    absent value is left untouched and reported as missing.
    """
    missing = []

    def repl(match):
        key = norm(match.group(1))
        val = (values.get(key) or "").strip()
        if not val:
            missing.append(match.group(1).strip())
            return match.group(0)
        return val

    return PLACEHOLDER_RE.sub(repl, text), missing


def merge(rows, headers, subject_t, body_t, email_col):
    seen = set()
    out = []
    for idx, row in enumerate(rows, start=1):
        values = {norm(h): row.get(h) for h in headers}
        to = (row.get(email_col) or "").strip()
        rec = {"row": idx, "to": to, "subject": "", "body": "",
               "status": "skipped", "reason": ""}
        if not to:
            rec["reason"] = "missing email"
        elif not EMAIL_RE.match(to):
            rec["reason"] = "invalid email"
        elif to.lower() in seen:
            rec["reason"] = "duplicate email"
        else:
            subject, m1 = render(subject_t, values)
            body, m2 = render(body_t, values)
            missing = list(dict.fromkeys(m1 + m2))
            if missing:
                rec["reason"] = "missing value for: " + ", ".join(missing)
            else:
                rec.update(subject=subject, body=body, status="drafted")
                seen.add(to.lower())
        out.append(rec)
    return out


def read_rows(path: Path):
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise MergeError(f"file not found: {path}")
    except UnicodeDecodeError:
        raise MergeError(f"{path} is not UTF-8. Re-save it as UTF-8 and try again.")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text, newline=""), dialect=dialect)
    if not reader.fieldnames:
        raise MergeError("the CSV is empty or has no header row")
    return reader.fieldnames, list(reader)


def find_email_col(headers, explicit):
    if explicit:
        if explicit not in headers:
            raise MergeError(f"column not found: {explicit!r}. Headers: {headers}")
        return explicit
    for h in headers:
        if norm(h) in EMAIL_NAMES:
            return h
    raise MergeError(f"could not find an email column. Headers: {headers}. Use --email-col.")


def run(args) -> int:
    csv_path = Path(args.csv)
    tpl_path = Path(args.template)
    dest = Path(args.output) if args.output else csv_path.with_name(csv_path.stem + ".drafts.csv")
    if dest.resolve() in (csv_path.resolve(), tpl_path.resolve()):
        raise MergeError("output path is the same as an input file")
    if dest.exists() and not args.force:
        raise MergeError(f"{dest} already exists (use --force to overwrite)")

    try:
        template_text = tpl_path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise MergeError(f"file not found: {tpl_path}")
    subject_t, body_t = parse_template(template_text)
    headers, rows = read_rows(csv_path)
    email_col = find_email_col(headers, args.email_col)

    results = merge(rows, headers, subject_t, body_t, email_col)
    with dest.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUT_COLS)
        writer.writeheader()
        writer.writerows(results)

    counts = Counter(r["status"] for r in results)
    print(f"Read {len(rows)} rows from {csv_path}", file=sys.stderr)
    print(f"  drafted: {counts.get('drafted', 0)}", file=sys.stderr)
    print(f"  skipped: {counts.get('skipped', 0)}", file=sys.stderr)
    for r in [r for r in results if r["status"] == "skipped"][:10]:
        print(f"    row {r['row']}: {r['reason']}", file=sys.stderr)
    print(f"Wrote {len(results)} rows to {dest}. Nothing was sent.", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="draftmerge",
        description="Turn a CSV and a template into email drafts. Never sends anything.")
    p.add_argument("csv", help="CSV file with a header row")
    p.add_argument("template", help="text template: first line 'Subject: ...', then the body")
    p.add_argument("-o", "--output", help="output CSV (default: <csv>.drafts.csv)")
    p.add_argument("--email-col", help="email column name (auto-detected if omitted)")
    p.add_argument("--force", action="store_true", help="overwrite the output file")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = p.parse_args(argv)
    try:
        return run(args)
    except MergeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
