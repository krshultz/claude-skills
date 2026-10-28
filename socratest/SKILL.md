---
name: socratest
description: Knowledge check before testing a ticket. Claude reads the issue and its sources, then quizzes the tester on what the ticket is testing -- what changes, where it lives in the app, the domain terms it assumes, what could go wrong, and exploratory test ideas -- grading each answer with a hint first and the full answer on a second miss. Gaps are saved to the glossary, project notes, and the run log. Use when the user types /socratest, or asks to be quizzed on a ticket before testing it.
argument-hint: "<ticket id>"
---

# Socratest

Many tickets are written by people who already know the product. A ticket body might talk about
"the links", "print", and "pick" without saying what any of them are, because the author does
that work every day. This skill closes that gap BEFORE testing starts: the tester attempts an
answer first, then Claude says how close they were. Trying first and checking afterward makes
the facts stick better than just reading an explanation would.

Assume the tester already knows how to test. Don't quiz them on testing concepts. Quiz them on
the app, the business domain, and this ticket.

**Before the first question, mention one thing in one line:** Claude Code's prompt suggestions
(grey predicted text in the input box) can show the answer, built from what is already in the
conversation. The tester may want to turn them off in `/config` for the quiz.

Arguments given: `$ARGUMENTS` (an issue id, e.g. SHOP-210). If none, ask which ticket via
AskUserQuestion.

## Step 1 -- Build the answer key (silently, before the first question)

Read, in full:
- The issue, with its comments and any attached documents (test plan, decision notes), if Claude
  can reach the tracker. If it cannot, ask the tester to paste the ticket.
- The project's notes, if there are any (a `CLAUDE.md`, a codebase-notes file the tester keeps),
  and the ticket's run log if one exists.
- The code the issue names, at the version actually under test (the ticket's branch or the test
  environment's branch, e.g. `git show origin/<branch>:<path>`). Read enough to answer each round
  from the source, not from the ticket's summary of it.

Write the key to the session scratchpad (not shown to the tester), one section per round below.
Tag every fact with its source (`issue body`, `test plan`, `file:line`, `project notes`) or mark
it **inferred**. An inferred fact may be offered as "probably" but never graded as right or
wrong. If the sources can't answer a round, say so when that round comes up. A ticket too thin to
answer is itself worth noting: offer to `/park` it as a ticket-clarity item, if `/park` is
installed.

## Step 2 -- The rounds

Five rounds, in this order. One question per message. Put it at the end of the message under the
heading **Your question:**. Free-text quiz answers are the whole point here, so they go in prose.
Decisions about the session itself (skip a round, stop early) still go through AskUserQuestion.

1. **What is this ticket testing?** In plain words: what was missing or broken, and what's
   different now. Open-ended on purpose; it shows which of the later rounds need the most time.
2. **Where does it live in the app?** Which page (full URL on the test environment), which link
   or button, who uses it (customer or staff), and what they're trying to get done.
3. **Domain terms.** Pick the 3-6 terms the ticket assumes without explaining (for a warehouse
   ticket: pick, pick sheet, back order, Paid -> Picking). Ask about them together ("say what you
   think each one means, and skip any you don't know").
4. **What could go wrong?** The risks this test has to cover, and especially any destructive or
   irreversible behavior (for example: a print link that moves every matching Paid order to
   Picking, not just the one on screen).
5. **Exploratory test ideas.** Ask for tests beyond the ticket's own checklist. Grade differently
   here, since there's no single right answer. Say which of the tester's ideas the checklist
   already covers, which are new and worth running, and which can't work (with the reason, from
   the source). Then add 2-3 of Claude's own. Offer to add the keepers to the run log's test list.

The tester can answer "skip" or "don't know" at any point. That reveals the full answer for that
round and moves on, with no hint step.

## Step 3 -- Grading each answer (hint first, then reveal)

- **First attempt:** say what they got right, specifically. Then give ONE hint pointing at the
  biggest missing or wrong piece, and ask them to try again. Correct anything wrong plainly ("not
  quite -- a pick sheet isn't the shipping label"); never let a wrong claim stand.
- **Every question about behavior names the state it asks about: BEFORE the fix or AFTER it.**
  "What happens when A posts B's ID?" has two correct answers (the bug, the fix), so a right
  answer to the other reading gets graded wrong -- which is maddening for the person answering.
  Write "After the fix, what happens when ..." or "Before the fix, ...", and when a round
  compares the two, say so: "Before vs after: ...". Same for the hint. An answer given to an
  ambiguous question is graded as correct for whichever reading it fits; the round is then
  re-asked unambiguously, not counted as a miss.
- **The retry question is still ONE question.** The "Your question (second try):" line asks about
  the one piece the hint pointed at, never two things joined by "and". If two pieces are missing,
  hint and ask about the bigger one; the reveal covers the other.
- **Second attempt (or a miss again):** give the full answer, a short paragraph per point, each with
  its source so they can check it ("from the test plan", "read in order_list.html").
- **Closeness** is said in words, not scores: "spot on", "mostly there -- missing X", "off track:
  X is actually Y".
- **Every grade (hit or miss) ends with "How you could have found this yourself:"** -- a short
  bulleted list of the concrete lookups that answer the round, one per source: the document and
  section ("test plan, core check 2 says ..."), the on-screen path ("checkout -> Delivery -> Edit
  address -> DevTools Elements, search type=hidden"), and the file and line in the repo with the
  search that finds it (`git grep -n "address_form" origin/<branch> -- src`). The point is to
  teach the lookup, not just the fact, so the tester can answer the next ticket's version without
  the quiz.
- Define every term in the answer at first use. If the tester uses a term loosely, give them the
  real name.
- Keep each reply to one screen.

## Step 4 -- Save what they didn't know

At the end (or if they stop early), save each gap and say exactly where it went:
- **Terms** (general or tooling vocabulary) -> append to a glossary file (default
  `~/.claude/glossary.md`, plain markdown). Check for an existing entry first; update it rather
  than duplicating.
- **App and domain facts** (what a pick sheet is, what the print link does to an order) -> the
  project notes file the tester keeps, with the source for each. If there is none, ask where they
  should go.
- **Run log** -> a `## Background (socratest <date>)` section in the ticket's run log, if the
  session keeps one: a 5-10 line plain-language brief of the ticket, so whoever reads the run log
  later doesn't need the quiz.
- Exploratory ideas they kept -> the run log's test list.

Then hand back to testing: one line on what's next (normally the first testing step).

## Don'ts

- Don't drive the browser. Opening a page for the tester to look at is fine; clicking and typing
  are theirs.
- Don't grade against inference. If the key says inferred, say so.
- Don't turn a round into a lecture. The hint is one sentence.
