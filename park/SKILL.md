---
name: park
description: Park a side finding during pair testing without derailing the current step -- a test to run later or a bug to file later -- into ~/.claude/parking-lot.md, then resume. "/park review" walks the open items one at a time when testing is done. Use when the user types /park, or says to park, save for later, or note a bug/test for later mid-test.
argument-hint: "[what you noticed] | review"
---

# Park

During pair testing, the tester drives the app and Claude guides: Claude gives one step, the
tester does it and reports back. When the tester notices something off to the side, they type
`/park` so it is saved without pulling the session off the step in progress. Parked items live in
ONE file, `~/.claude/parking-lot.md`, so they survive any session ending.

Items are usually reviewed days or weeks later, in a different session, by someone (the tester or
Claude) who remembers none of it. So every entry must carry enough to rebuild the scene without
the conversation that produced it.

Arguments given: `$ARGUMENTS`

If the arguments are exactly `review`, go to **Review mode**. Otherwise, **Capture mode**.

## Capture mode

The goal is to be fast and then get out of the way. Do NOT investigate the finding: no source
reading, no browser checks, no issue-tracker searches. That is what review mode (and
`/park-audit`, if installed) is for.

1. **Get the text.** If arguments were given, that is the finding, verbatim. If none, ask what the
   tester noticed, as the only question this turn; ask the type (step 2) after they answer.
2. **Ask the type** with AskUserQuestion, one question, two options: "Bug to file later" and
   "Test to do later". If the arguments already make it unambiguous ("bug:" or "test:", or a plain
   description of something broken), skip the question.
3. **Add context Claude already has in this conversation** -- never go looking for it. Include
   every field that is known; leave out any that is not:
   - **ticket**: the ticket being tested, with its topic, e.g. `SHOP-142 [Coupon codes at checkout]`
   - **step**: the step in progress, by its label in the run log, e.g. `edge case E2`
   - **doing**: what the tester was trying to do at that moment, in one clause, e.g. `applying a
     second coupon to check that only one is allowed`
   - **page**: the page or URL
   - **test data**: the order numbers, item IDs, account or coupon IDs in play, and their state at
     that moment, e.g. `coupon SAVE10 expired yesterday; cart has item 1017, qty 2`
   - **evidence**: screenshot number if one was shared, exact error or message text
   - **run log**: the file and step where the full story lives, if the session keeps one
   - **hunch**: Claude's opinion, if any, always labeled `hunch, not checked`. Never state a cause
     as fact at capture time.
4. **Give it an ID.** Every item gets a permanent ID, `<initials>-<three-digit number>`, e.g.
   `JD-026`. Initials are the first letters of the first and last words of `git config user.name`
   ("Jane Doe" -> `JD`). The number is one more than the highest number already used with those
   initials anywhere in the file (Open or Closed). The ID never changes, even if the line is edited
   or the item is closed; `/park-audit` keys its write-ups to it. The initials keep IDs from
   colliding if parking lots from different people are ever merged.
5. **Append** under `## Open` in the parking-lot file (create the file from the layout below if it
   is missing). One item per line, ASCII only, no line breaks inside an item, the ID first:

   ```
   - [ ] JD-003 | 2026-10-05 | BUG | "The expired coupon still applied -- total dropped by 10%." | during: SHOP-142 [Coupon codes at checkout], edge case E2 | doing: applying a second coupon to check that only one is allowed | page: /cart | test data: coupon SAVE10 expired 2026-10-04; cart has item 1017, qty 2 | evidence: tester's screenshot 3 -- cart shows "SAVE10 applied" | run log: shop-142-test-run.md, step E2
   ```

   Use the real current date. The tester's words go in quotes exactly as written.
6. **Confirm in one line** ("Parked as bug JD-003.") and **resume**: name the step that was in
   progress and what result is still owed, in one sentence. Do not repeat the full instruction if
   the tester already has it -- say what is outstanding ("Still waiting on E2: the cart total
   after the second coupon."). If no step was in progress, just confirm.

If this session keeps a working-state or run-log file, add one line there pointing at the parked
item; do not copy the item.

## Review mode

Run when pair testing is done. One item at a time -- never hand the tester the whole list as a
to-do.

1. Read the whole parking-lot file. Say in one line how many items are open (bugs vs tests).
2. **Show the list so the tester picks the order.** One line per open item, numbered oldest
   first, grouped by the test run it came from (e.g. "From SHOP-142's run, 10/5"), each line a
   plain-words summary marked BUG or TEST. Then ask which item to start with. Oldest first is
   only the default.
3. **Rebuild before presenting.** If the entry is thin, first read the run log it points to (and
   the ticket, if Claude can reach the tracker) to recover the scene. Never present an item from
   memory. If something cannot be recovered, say so rather than filling the gap.
4. **Present the chosen item from scratch**, as if the tester has never seen it, under these five
   labels:
   - **Where:** the page, item, or order
   - **What you were doing:** the ticket, the step, and what that step was for
   - **What you saw:** the tester's words, plus what the screen showed
   - **What's known:** what is verified (and how) versus what is a guess. If the line carries a
     "code audit" pointer (written by `/park-audit`), read that item's newest section in
     `~/.claude/park-audits.md` (sections are headed `## <title> (<ID>)`; the newest is lowest in
     the file) and summarize its verdict, the why, and any existing ticket it found, naming the
     audit date and commit.
   - **History:** earlier reviews of this item, or "first time in review"

   Then ask ONE question:
   - For a bug: "Investigate and draft a ticket" / "Leave open" / "Drop it"
   - For a test: "Run it now, tester drives" / "Run it now, tester drives, Claude checks" /
     "Run it now, Claude drives" / "Leave open" / "Drop it". Offer the two Claude options only
     if Claude has browser access (for example, Claude in Chrome).
5. Act on the answer:
   - **Investigate / run**: do it as normal testing work. For a bug, reproduce it or read the
     source, draft the ticket (see "Drafting a bug ticket" below), and SHOW the tester the draft.
     Nothing is filed without the tester's explicit approval.
   - **Before asking which tickets to draft** (or how many), search the issue tracker for
     existing tickets first, if Claude has access, and report what was found and what the search
     covered (some tracker searches match titles only). The number of new tickets depends on what
     already exists.
   - **Tester drives**: the tester runs the test and reports results; Claude gives ONE action per
     turn and does not look at the page. The tester's report is the evidence, labeled as theirs.
   - **Tester drives, Claude checks**: give ONE action per turn; after the tester reports, read
     the page in the browser to confirm what they saw, then give the next action. Claude does not
     click or type.
   - **Drop**: ask for nothing more; record it as dropped.
6. When an item is finished, move it from `## Open` to `## Closed` (ID unchanged), changing `[ ]`
   to `[x]` and appending the outcome and date, e.g. `| closed 2026-10-07: filed SHOP-150` or
   `| closed 2026-10-07: dropped, works as intended`.
7. Then offer the next item, or stop if the tester wants to stop. Items left open stay open.

## Drafting a bug ticket

Every drafted bug ticket gets its own **Steps to Recreate** section, separate from the narrative.
Someone recreating the bug -- the tester or a developer -- should not have to dig the steps out of
paragraphs.

- **Numbered list, one action per step, one line each.** Start each step with a verb: "Go to",
  "Click", "Type", "Set". No reasoning or backstory inside the steps; that goes in the narrative.
- **Start from a known state.** Above step 1, a short **Setup** line lists what must already be
  true: which account is signed in, and the test data with exact IDs.
- **Exact values.** Full URL or path, the exact text to type, and buttons or links named by their
  on-screen label in quotes ("Apply coupon").
- **End with Expected and Actual**, one line each. Actual quotes the exact error or message text.
- **Screenshots go directly below the step they belong to**, so the reader reads the step and then
  sees its picture. Screenshots are welcome but not required; some bugs need none.
- **Screenshots can also go under Expected or Actual**: under Actual to show the wrong result,
  and under Expected when there is a picture of the correct behavior to compare against.
- **When posting to the tracker, embed each screenshot where it belongs**, under its step,
  Expected, or Actual line. An attachment alone does not count -- the reader must see the picture
  in place.
- **Caption a result screenshot as "after <action>", and describe that result in the step text.**
  A picture taken after a click sits under the step that says to click, so without that, the
  reader takes it as the before state.
- **Say whether screenshots exist.** If there are none, say so plainly ("No screenshots for this
  one") so the tester can decide whether the ticket needs one.
- **Frequency line after Actual**: how often the bug has been seen, from what actually happened,
  e.g. "Frequency: seen once, not yet retried" or "Frequency: 3 of 3 tries". If a step is a guess,
  say so there too.

Example:

```
### Steps to Recreate
Setup: signed in as a customer; coupon SAVE10 expired yesterday; cart empty.
1. Go to /item/1017
2. Click "Add to Cart"
3. Go to /cart
4. In the Coupon field, type SAVE10
5. Click "Apply coupon"
   [tester's screenshot 3, after clicking "Apply coupon": cart shows "SAVE10 applied", total reduced 10%]
Expected: "This coupon has expired"; total unchanged.
Actual: "SAVE10 applied"; total reduced by 10%.
Frequency: 2 of 2 tries.
```

## File layout

```
# Parking lot

Side findings parked during pair testing with /park. Open items first; closed items keep their outcome.
Code-audit write-ups from /park-audit live in park-audits.md, keyed by item ID.

## Open

## Closed
```
