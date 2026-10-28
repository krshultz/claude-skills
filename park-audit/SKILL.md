---
name: park-audit
description: Supplement to /park. Checks open items in ~/.claude/parking-lot.md against the source code with read-only Opus park-auditor subagents -- one per group of related items -- judging whether each parked bug/test/research item holds up, whether it was fixed since parking, whether it is pre-existing or recent, and whether a tracker ticket already covers it. Full write-ups go to park-audits.md keyed by item ID; the parking-lot line gets a short pointer. Re-runs are incremental: an item is re-audited only if code its last audit read has changed. Use when the user types /park-audit, or asks to audit, verify, or check the parked items against the code.
argument-hint: "[max auditors this run, default 3] [full]"
---

# Park audit

`/park` captures side findings fast, with no investigation, and `/park review` walks them one at
a time days later. This skill sits between them: before a review, it has open items checked
against the code by a careful reader, so the reviewer starts from evidence instead of a mid-test
hunch.

Auditors are `park-auditor` subagents (defined in `~/.claude/agents/park-auditor.md`, pinned to
Opus, read-only tools). They never write anything; this session is the only writer of the two
files, so parallel agents cannot clobber each other's edits.

Arguments given: `$ARGUMENTS`

- A number N: launch at most N auditors this run (default 3). Items left over are reported as
  "not yet audited -- run /park-audit again".
- `full`: ignore the incremental check and re-audit every open item (still capped at N auditors).

## Setup

The repository, its remote and base branch, the code host (for links), and the issue tracker
are set in the CONFIG block at the top of `park_audit.py` in this skill's folder. That is the one
place they live. Run `python3 -I ~/.claude/skills/park-audit/park_audit.py config` to print them;
below, `<repo>`, `<remote>`, and `<branch>` mean those values.

## The two files

- `~/.claude/parking-lot.md` -- the items, written by `/park`. Each open line starts
  `- [ ] <ID> | <date> | <TYPE> | ...`, where the ID is like `JD-004`.
- `~/.claude/park-audits.md` -- the full write-ups. One section per audit of one item, headed
  `## <plain-words title> (<ID>)`, with an "Audited" line giving the date and the commit. An item
  audited more than once has several sections with the same heading; the newest (lowest) is
  current. Code, commit, and ticket references are links pinned to the audited commit.

The helper `park_audit.py` does the mechanical parts: the incremental check, and turning auditor
blocks into sections (it builds every link and checks every citation). Run it with
`python3 -I ~/.claude/skills/park-audit/park_audit.py ...`. It creates `park-audits.md` with its
header if the file is missing.

## Steps

1. **Read both files in full.** Collect every line under `## Open` that starts with `- [ ]`.
   If any lacks an ID, assign one using `/park`'s rule (read the "Give it an ID" step of
   `~/.claude/skills/park/SKILL.md`), oldest first, and say so in the report. If there are no open
   items, say so and stop.

2. **Fetch and pin the commit.** The audit is against the base branch as it is on the remote now:
   ```
   git -C <repo> fetch <remote> <branch>
   git -C <repo> rev-parse <remote>/<branch>
   ```
   Record the full and short SHA (a SHA is the ID of one commit, one saved snapshot of the code).

3. **Incremental check -- decide which items need an auditor.** If `full` was given, every open
   item **needs audit** ("full re-run"). Otherwise run
   ```
   python3 -I ~/.claude/skills/park-audit/park_audit.py check <full sha>
   ```
   It prints one line per open item: ID, status, detail. For each item it takes the newest
   section's commit and "Files read" list and runs `git diff --quiet` on those files between that
   commit and the new one.
   - `never` -> **needs audit** ("never audited").
   - `holds` -> **still holds**: none of the code the verdict rests on changed; no auditor,
     nothing written.
   - `changed` -> **needs audit** ("changed since last audit: <files>").
   - `error` -> **needs audit** ("could not check: <detail>").
   This check only sees files the last auditor read. A change elsewhere (a new caller, a new
   setting) can go unnoticed; that is the accepted trade-off, and `full` is the escape hatch.
   The check compares WHOLE files, not the line ranges an auditor cited. Big shared files change
   often, so this re-audits items more than strictly needed. That is deliberate: skipping on line
   ranges could miss a regression introduced elsewhere in a changed file. Do not narrow it to line
   ranges.

4. **Group the items that need an audit.** Put items in one group when an auditor would read the
   same code for them: the same page, controller, or feature (e.g. gift cards, checkout, the
   order-detail page). At most 5 items per group; an item that shares code with nothing goes
   alone. Groups are your judgment from the entries' text (pages, URLs, tickets, wording), not
   from reading code. Order groups oldest-item first; take the first N groups this run, and hold
   the rest.

5. **If at least one group runs, prepare a read-only copy of the code:**
   ```
   git -C <repo> worktree add --detach <tmp>/park-audit-<short sha> <full sha>
   ```
   (A worktree is a second working folder backed by the same repository, so the auditors can read
   files at that commit without touching the user's checkout.) Use this session's scratchpad
   directory for `<tmp>` if it has one.

6. **Say what is about to run, in one line:** "Auditing X items in G groups against <branch>
   <short sha> with G Opus auditors; S still hold, H held for a later run." Then launch the groups,
   **all in one message**, one Agent call per group, `subagent_type: "park-auditor"`,
   `run_in_background: true`, description `Audit parked: <3-5 word topic>`. The prompt for each:
   ```
   Today: <YYYY-MM-DD>
   Repository: <repo>
   Base branch: <branch>
   Read-only checkout of the base branch: <worktree path>
   Audited commit: <full sha>

   Parked entries (verbatim, one per line):
   <each whole entry line in the group>
   ```
   For an item being re-audited, add after its line: `Previous audit: <date> at <short sha>,
   verdict <VERDICT>; changed since: <files>` so the auditor knows where to look first.

7. **As each result arrives, check it, then write it.** The auditor returns one block per item.
   - **Check the format:** one block per item sent, every field present, ID matches, VERDICT uses
     one of the listed values, FILES READ is a list of repo-relative paths. A block that fails is
     not written; note the item as "audit failed" for the report.
   - **Spot-check one citation per block:** open one code marker from WHY (`{path:line}`) in the
     worktree and confirm it says what the auditor claims. If it does not, do not write that block;
     report it as "audit unreliable: <what was wrong>". Never correct an auditor's claim from your
     own memory. Record what you checked as one line: `Claude opened {<path>:<lines>} on
     <YYYY-MM-DD>; <what it said, and whether it matches>`.
   - **Write it with the helper.** Re-read `parking-lot.md` first (the user may have parked
     something meanwhile). Save the group's passing blocks to a file in the scratchpad and the spot
     checks to a JSON file (`{"<ID>": "<spot-check line>"}`), then run
     ```
     python3 -I ~/.claude/skills/park-audit/park_audit.py write <blocks file> --commit <full sha> --date <YYYY-MM-DD> --group <all IDs sent to that auditor, comma-separated> --spot <json file>
     ```
     It appends one section per block to the END of `park-audits.md` (never editing an earlier
     section) and appends this pointer to the END of each item's parking-lot line, leaving the
     tester's words and earlier pointers alone:
     ` | code audit <YYYY-MM-DD> (<branch> <short sha>): <VERDICT>, <confidence word> -- full write-up: park-audits.md <ID>`
     If it prints "NOT WRITTEN", nothing was written for the group. Each problem names the item: a
     citation that does not exist at that commit, a line range past the end of the file, an
     unknown commit, a missing field. Drop the failing block from the file and run it again for the
     rest; report the dropped item as "audit unreliable: <the problem>".
   - This skill never closes, drops, or reorders items, never files or comments on tickets, and
     never runs anything in the browser. A tracker match or a FIXED SINCE PARKED verdict is
     information for `/park review`, where the user decides.

8. **Clean up** once every auditor has finished:
   `git -C <repo> worktree remove --force <worktree path>`.

9. **Report** in a final message (no tool call after it), one screen at most:
   - Audited this run, one line per item grouped by verdict -- CONTRADICTED and FIXED SINCE
     PARKED first (those change what the user thought they knew), then CONFIRMED / PARTLY, then
     CAN'T SETTLE. Each line: ID, BUG/TEST, a plain-words summary, the verdict, and the one
     sentence that matters most (e.g. "already filed as SHOP-118 [Refunded gift card keeps
     balance]").
   - Still holds: the IDs whose code did not change, in one line.
   - Not yet audited: the IDs held for a later run, in one line, with "run /park-audit again".
   - Any "audit failed" or "audit unreliable" items, with the reason.
   - Where the detail lives: `~/.claude/park-audits.md`; `/park review` shows it under
     "What's known".

10. If this session keeps a working-state file, add one line: date, "/park-audit: X audited, S
    still hold, H not yet, against <branch> <short sha>; write-ups in park-audits.md". Do not copy
    the verdicts there.
