#!/usr/bin/env python3
# Helper for the /park-audit skill. Three jobs:
#
#   config
#       Prints the repository, remote, and base branch from the CONFIG block below, so the skill
#       reads them from one place.
#
#   check <full sha>
#       The incremental check. For every open item in parking-lot.md, find its newest section in
#       park-audits.md and diff the files that audit read between its commit and <full sha>.
#       Prints one tab-separated line per item: ID, status (never | holds | changed | error),
#       detail. Whole files are compared, never line ranges, so a change elsewhere in a file the
#       verdict rests on is never skipped.
#
#   write <blocks file> --commit <full sha> --date <YYYY-MM-DD> --group <ID,ID,...>
#         [--spot <json file>] [--auditor <text>] [--out <file>] [--no-pointer]
#       Turns auditor blocks into park-audits.md sections and appends the pointer to each item's
#       parking-lot line. Citations are written by the auditor as markers and turned into
#       commit-pinned links here, so no agent ever types a URL:
#           {path/from/repo/root.py:12-20}   {path/from/repo/root.py:12}   {path/from/repo/root.py}
#           {commit:<sha, short or full>}     {SHOP-123}
#       Every file marker is checked against the audited commit (file exists, lines in range) and
#       every commit marker must resolve. Any failure stops the write for the whole run and is
#       printed; nothing is half-written.
#       A block may carry COMMIT:, AUDITED:, AUDITOR:, SPOT CHECK: header lines; they override the
#       command-line values for that block (used when converting older write-ups).

import argparse
import json
import os
import re
import subprocess
import sys

# ---------- CONFIG: edit these to match your setup ----------

REPO = os.path.expanduser("~/Repositories/your-project")  # local clone to audit against
REMOTE = "origin"
BRANCH = "main"  # the base branch audits are pinned to

# Code host, for commit-pinned links: "github", "gitlab", "bitbucket", or "none" (plain text).
CODE_HOST = "github"
REPO_URL = "https://github.com/your-org/your-project"

# Issue key prefix, e.g. "SHOP" for SHOP-123, and a URL template with {id}. Leave ISSUE_URL empty
# to print issue keys as plain text.
ISSUE_PREFIX = "SHOP"
ISSUE_URL = ""  # e.g. "https://linear.app/your-team/issue/{id}"

LOT = os.path.expanduser("~/.claude/parking-lot.md")
AUDITS = os.path.expanduser("~/.claude/park-audits.md")

# ---------- end of CONFIG ----------

HEADER_FIELDS = ["ID", "TITLE", "VERDICT", "CONFIDENCE", "TO SETTLE", "ORIGIN", "FILES READ"]
OPTIONAL_FIELDS = ["COMMIT", "AUDITED", "AUDITOR", "SPOT CHECK"]
BODY_FIELDS = ["WHY", "HUNCHES", "SINCE PARKED", "ORIGIN DETAIL", "TRACKER"]

AUDITS_HEADER = f"""# Park audits

Full code-audit write-ups for items in parking-lot.md, written by /park-audit. Each section is one audit of one item; its heading is a plain-words title with the item's ID in brackets. An item audited more than once has several sections with the same heading; the "Audited" line tells them apart, the newest (lowest in the file) is current, and older ones stay as history. Every step under "Why" was read in the code at the audited commit unless it is marked *(inferred)*. Code and commit references are pinned to that commit, so line numbers do not drift. "Files read" (under Audit details) is what the incremental check compares: if none of those files changed between the audited commit and today's {BRANCH}, the verdict still holds and the item is not re-audited.
"""


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True)


def ascii_only(text):
    swaps = {"—": "--", "–": "-", "→": "->", "‘": "'", "’": "'",
             "“": '"', "”": '"', "…": "...", " ": " "}
    for k, v in swaps.items():
        text = text.replace(k, v)
    return text.encode("ascii", "replace").decode()


# ---------- links ----------

def file_url(commit, path, a=None, b=None):
    if CODE_HOST == "none":
        return ""
    kind = {"github": "blob", "gitlab": "-/blob", "bitbucket": "src"}[CODE_HOST]
    base = f"{REPO_URL}/{kind}/{commit}/{path}"
    if not a:
        return base
    if CODE_HOST == "bitbucket":
        return base + (f"#lines-{a}:{b}" if b else f"#lines-{a}")
    if CODE_HOST == "gitlab":
        return base + (f"#L{a}-{b}" if b else f"#L{a}")
    return base + (f"#L{a}-L{b}" if b else f"#L{a}")


def commit_url(commit):
    if CODE_HOST == "none":
        return ""
    path = {"github": "commit", "gitlab": "-/commit", "bitbucket": "commits"}[CODE_HOST]
    return f"{REPO_URL}/{path}/{commit}"


def linked(label, url):
    return f"[`{label}`]({url})" if CODE_HOST != "none" else f"`{label}`"


# ---------- reading the two files ----------

def lot_items():
    # Returns {ID: (open?, date, type, text)} from parking-lot.md.
    items = {}
    for line in open(LOT).read().split("\n"):
        m = re.match(r"- \[( |x)\] ([A-Z]+-\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+)", line)
        if m:
            items[m.group(2)] = (m.group(1) == " ", m.group(3).strip(), m.group(4).strip(), m.group(5).strip())
    return items


def newest_sections():
    # Returns {ID: section text} for the LAST section of each ID in park-audits.md.
    if not os.path.exists(AUDITS):
        return {}
    text = open(AUDITS).read()
    parts = re.split(r"(?m)^(?=## )", text)
    found = {}
    for p in parts:
        m = re.match(r"## .*\(([A-Z]+-\d+)\)\s*$", p.split("\n", 1)[0])
        if m:
            found[m.group(1)] = p
    return found


def section_commit_and_files(section):
    m = re.search(r"^- \*\*Commit:\*\* `([0-9a-f]{40})`", section, re.M)
    commit = m.group(1) if m else None
    files = []
    after = section.split("**Files read**", 1)
    if len(after) == 2:
        for line in after[1].split("\n")[1:]:
            fm = re.match(r"\s+- `([^`]+)`\s*$", line)
            if fm:
                files.append(fm.group(1))
            elif line.strip():
                break
    return commit, files


# ---------- check ----------

def cmd_check(new_sha):
    sections = newest_sections()
    for item_id, (is_open, _d, _t, _x) in lot_items().items():
        if not is_open:
            continue
        if item_id not in sections:
            print(f"{item_id}\tnever\tnever audited")
            continue
        commit, files = section_commit_and_files(sections[item_id])
        if not commit or not files:
            print(f"{item_id}\terror\tcould not read the commit or Files read from its newest section")
            continue
        r = git("diff", "--quiet", commit, new_sha, "--", *files)
        if r.returncode == 0:
            print(f"{item_id}\tholds\tunchanged since {commit[:9]}")
        elif r.returncode == 1:
            changed = git("diff", "--name-only", commit, new_sha, "--", *files).stdout.split()
            print(f"{item_id}\tchanged\t{commit[:9]}; changed since: {', '.join(changed)}")
        else:
            print(f"{item_id}\terror\tgit diff failed: {r.stderr.strip()[:200]}")


# ---------- write ----------

def parse_blocks(text):
    blocks = []
    for chunk in re.split(r"(?m)^(?=ID:)", text.strip()):
        if not chunk.strip():
            continue
        block = {}
        current = None
        for line in chunk.rstrip().split("\n"):
            if line.strip() == "END":
                break
            body = re.match(r"^(%s):\s*$" % "|".join(BODY_FIELDS), line)
            head = re.match(r"^(%s):\s*(.*)$" % "|".join(HEADER_FIELDS + OPTIONAL_FIELDS), line)
            if body:
                current = body.group(1)
                block[current] = []
            elif head and current is None:
                block[head.group(1)] = head.group(2).strip()
            elif current is not None:
                block[current].append(line)
        for f in BODY_FIELDS:
            if f in block:
                block[f] = "\n".join(block[f]).strip("\n")
        blocks.append(block)
    return blocks


class Linker:
    def __init__(self, commit):
        self.commit = commit
        self.errors = []
        self.line_counts = {}

    def file_lines(self, path):
        if path not in self.line_counts:
            # Read raw bytes: some files (SQL dumps from some tools) are UTF-16, not UTF-8.
            r = subprocess.run(["git", "-C", REPO, "show", f"{self.commit}:{path}"], capture_output=True)
            if r.returncode:
                self.line_counts[path] = None
            else:
                raw = r.stdout
                utf16 = raw[:2] in (b"\xff\xfe", b"\xfe\xff")
                content = raw.decode("utf-16" if utf16 else "utf-8", errors="replace")
                self.line_counts[path] = content.count("\n") + 1
        return self.line_counts[path]

    def full_sha(self, short):
        r = git("rev-parse", "--verify", "--quiet", short + "^{commit}")
        return r.stdout.strip() if r.returncode == 0 else None

    def link_line(self, line):
        seen = set()

        def file_marker(m):
            path, lines = m.group(1), m.group(2)
            count = self.file_lines(path)
            if count is None:
                self.errors.append(f"no such file at {self.commit[:9]}: {path}")
                return m.group(0)
            label = os.path.basename(path)
            a = b = None
            if lines:
                a, _, b = lines.partition("-")
                if int(a) > count or (b and (int(b) > count or int(b) < int(a))):
                    self.errors.append(f"line range {lines} outside {path} ({count} lines)")
                label = lines if path in seen else f"{label}:{lines}"
            seen.add(path)
            return linked(label, file_url(self.commit, path, a, b))

        def commit_marker(m):
            full = self.full_sha(m.group(1))
            if not full:
                self.errors.append(f"unknown commit: {m.group(1)}")
                return m.group(0)
            return linked(full[:9], commit_url(full))

        def issue_marker(m):
            key = m.group(1)
            return f"[{key}]({ISSUE_URL.format(id=key)})" if ISSUE_URL else key

        line = re.sub(r"\{commit:([0-9a-f]{7,40})\}", commit_marker, line)
        line = re.sub(r"\{(%s-\d+)\}" % re.escape(ISSUE_PREFIX), issue_marker, line)
        line = re.sub(r"\{([\w./-]+\.[A-Za-z]+)(?::(\d+(?:-\d+)?))?\}", file_marker, line)
        return line

    def link(self, text):
        return "\n".join(self.link_line(l) for l in text.split("\n"))


def build_section(block, args, spot, lot):
    item_id = block["ID"]
    commit_in = block.get("COMMIT", args.commit)
    linker = Linker(commit_in)
    commit = linker.full_sha(commit_in) or commit_in
    linker.commit = commit
    date = block.get("AUDITED", args.date)
    if item_id not in lot:
        linker.errors.append(f"{item_id} is not in parking-lot.md")
        return None, None, linker.errors
    _open, parked, kind, text = lot[item_id]
    quote = text.replace('\\"', '"')
    if len(quote) > 100:
        quote = quote[:100].rsplit(" ", 1)[0] + " ..."
    article = "an" if kind[:1].upper() in "AEIOU" else "a"
    group = [g for g in args.group.split(",") if g and g != item_id]
    auditor = block.get("AUDITOR") or args.auditor or (
        "Opus, grouped with " + ", ".join(group) if group else "Opus, alone")
    spot_text = block.get("SPOT CHECK") or spot.get(item_id)
    if not spot_text:
        linker.errors.append(f"{item_id}: no spot check recorded")
    files = [f.strip() for f in block["FILES READ"].split(",") if f.strip()]
    for f in files:
        if ":" in f or f.startswith("/") or linker.file_lines(f) is None:
            linker.errors.append(f"{item_id}: bad Files read entry: {f}")
    out = [
        f"## {block['TITLE']} ({item_id})",
        "",
        f"- **Parked:** {parked} as {article} {kind} -- {quote}",
        f"- **Audited:** {date} against {BRANCH} {{commit:{commit}}}",
        f"- **Verdict:** {block['VERDICT']}",
        f"- **Confidence:** {block['CONFIDENCE']}",
        f"- **To settle:** {block['TO SETTLE']}",
        "",
        "### Why", "", block["WHY"], "",
        "### Hunches in the entry", "", block["HUNCHES"], "",
        "### Since parked", "", block["SINCE PARKED"], "",
        f"### Origin: {block['ORIGIN']}", "", block["ORIGIN DETAIL"], "",
        "### Tracker", "", block["TRACKER"], "",
        "### Audit details", "",
        f"- **Auditor:** {auditor}",
        f"- **Spot check:** {spot_text}",
        "- **Files read** (what the next run compares for changes):",
    ] + [f"    - `{f}`" for f in files]
    section = linker.link("\n".join(out))
    # The full SHA, written after linking so the check can read it whatever the code host.
    section += f"\n- **Commit:** `{commit}`\n"
    leftover = re.findall(r"\{[^{}\s]+\}", section)
    if leftover:
        linker.errors.append(f"{item_id}: unconverted markers {leftover[:5]}")
    confidence_word = block["CONFIDENCE"].split()[0] if block["CONFIDENCE"] else "?"
    pointer = (f" | code audit {date} ({BRANCH} {commit[:9]}): {block['VERDICT']}, "
               f"{confidence_word} -- full write-up: park-audits.md {item_id}")
    return ascii_only(section), ascii_only(pointer), linker.errors


def cmd_write(args):
    blocks = parse_blocks(open(args.blocks).read())
    spot = json.load(open(args.spot)) if args.spot else {}
    lot = lot_items()
    sections, pointers, errors = [], {}, []
    for b in blocks:
        missing = [f for f in HEADER_FIELDS + BODY_FIELDS if not b.get(f)]
        if missing:
            errors.append(f"{b.get('ID', '?')}: missing fields {missing}")
            continue
        section, pointer, errs = build_section(b, args, spot, lot)
        errors += errs
        if section:
            sections.append(section)
            pointers[b["ID"]] = pointer
    if errors:
        print("NOT WRITTEN. Problems:")
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    out = args.out or AUDITS
    if not os.path.exists(out):
        open(out, "w").write(AUDITS_HEADER)
    with open(out, "a") as f:
        for s in sections:
            f.write("\n" + s)
    if not args.no_pointer:
        lines = open(LOT).read().split("\n")
        for n, line in enumerate(lines):
            for item_id, p in list(pointers.items()):
                if line.startswith(f"- [ ] {item_id} |"):
                    lines[n] = line + p
                    del pointers[item_id]
        open(LOT, "w").write("\n".join(lines))
    print("written: " + ", ".join(b["ID"] for b in blocks) + f" -> {out}")
    if pointers and not args.no_pointer:
        print("no open parking-lot line found for: " + ", ".join(pointers))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("config")
    c = sub.add_parser("check")
    c.add_argument("sha")
    w = sub.add_parser("write")
    w.add_argument("blocks")
    w.add_argument("--commit", required=True)
    w.add_argument("--date", required=True)
    w.add_argument("--group", default="")
    w.add_argument("--spot")
    w.add_argument("--auditor")
    w.add_argument("--out")
    w.add_argument("--no-pointer", action="store_true")
    a = p.parse_args()
    if CODE_HOST not in ("github", "gitlab", "bitbucket", "none"):
        sys.exit(f"CODE_HOST must be github, gitlab, bitbucket, or none, not {CODE_HOST!r}")
    if a.cmd == "config":
        print(f"repo\t{REPO}\nremote\t{REMOTE}\nbranch\t{BRANCH}")
    elif a.cmd == "check":
        cmd_check(a.sha)
    else:
        cmd_write(a)


if __name__ == "__main__":
    main()
