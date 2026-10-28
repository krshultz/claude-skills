# claude-skills

Skills for [Claude Code](https://claude.com/claude-code) that I built for my own QA work. A skill
is a packaged set of instructions Claude loads on demand, when a task matches it or when you type
its name as a slash command.

## park

A parking lot for side findings during exploratory testing.

When you test with Claude as a pair (you drive the app, Claude guides and keeps notes), you notice
things off to the side: a field that accepts a negative quantity, a button label that looks wrong,
an edge case worth trying later. Chasing each one derails the test you're running. Ignoring them
means losing them.

`/park` saves the finding in one line and gets you back to work:

```
/park the expired coupon still applied -- total dropped by 10%
```

Claude records your words verbatim, plus the context it already has from the session: the ticket,
the step you were on, what you were doing, the page, the test data in play, any screenshot or
error text, and its own hunch, clearly labeled as unchecked. Then it tells you which step you were
on and what result is still owed.

Each entry gets a permanent ID (your initials plus a number) and looks like this (one line in
`~/.claude/parking-lot.md`):

```
- [ ] JD-003 | 2026-10-05 | BUG | "The expired coupon still applied -- total dropped by 10%." | during: SHOP-142 [Coupon codes at checkout], edge case E2 | doing: applying a second coupon to check that only one is allowed | page: /cart | test data: coupon SAVE10 expired 2026-10-04; cart has item 1017, qty 2 | evidence: tester's screenshot 3 -- cart shows "SAVE10 applied" | run log: shop-142-test-run.md, step E2
```

When the session is over, `/park review` walks the open items one at a time. Each item is
rebuilt from scratch, because days or weeks later nobody remembers the scene:

- **Where:** the page, item, or order
- **What you were doing:** the ticket, the step, and what that step was for
- **What you saw:** your words, plus what the screen showed
- **What's known:** what is verified (and how) versus what is a guess
- **History:** earlier reviews of this item

You pick what happens next: investigate and draft a ticket, run the test now, leave it open, or
drop it. Drafted bug tickets get a numbered **Steps to Recreate** section, with screenshots
placed under the step they belong to, so a developer can reproduce the bug without reading
paragraphs.

### Design choices

- **Capture is fast; triage is later.** Capture mode never investigates. Reading code or
  searching the tracker mid-test is the derailment `/park` exists to prevent.
- **Every entry stands alone.** The entry has to make sense in a new session, to someone who
  wasn't there, which might be you three weeks from now.
- **Guesses are labeled.** Claude's theories are marked `hunch, not checked` at capture, and
  review keeps verified facts apart from guesses.
- **Nothing is filed without your approval.** Claude drafts tickets; you decide what gets filed.

### Install

Copy the `park` folder into your personal skills folder:

```
cp -r park ~/.claude/skills/
```

Or into a project's `.claude/skills/` to share it with everyone working in that repo. Claude Code
picks it up in the next session. The parking-lot file is created on first use; to keep it
somewhere else, change the path in `SKILL.md`.

Optional: checking your work in the browser during review needs Claude to have browser access,
such as [Claude in Chrome](https://claude.com/chrome). Searching for existing tickets needs access
to your issue tracker. Without them, the skill skips those options.

## park-audit

A code check for parked items, between `/park` and `/park review`.

A parked bug is a mid-test hunch. Before you sit down to review it, `/park-audit` has each open
item checked against the source by a careful, read-only reader, so the review starts from
evidence:

```
/park-audit        # audit up to 3 groups of items
/park-audit 5 full # up to 5 groups, re-audit everything
```

Related items (same page, same feature) are grouped and handed to `park-auditor` subagents, one
per group, running in parallel on a read-only copy of the code at the current base branch. A
subagent is a separate Claude instance with its own context and a restricted set of tools. For
each item, the auditor answers:

- Does the code produce what was parked (or predict the test's outcome, or answer the question)?
- Was each of Claude's capture-time hunches right, wrong, or partly right?
- Was it fixed since it was parked?
- Is it pre-existing, or did a recent change introduce it (from `git blame`)?
- Is there already a ticket for it, if the auditor can search your tracker?

The full write-up goes to `~/.claude/park-audits.md`, one section per item, with every code
citation as a link pinned to the audited commit. The parking-lot line gets a one-line pointer,
and `/park review` shows the verdict under "What's known".

### Design choices

- **Auditors never write.** They return fixed-format blocks; the main session checks the format,
  opens one citation per block to confirm it says what the auditor claims, and is the only writer.
- **No agent types a URL.** Auditors cite code as markers (`{src/cart.py:120-134}`); a helper
  script turns them into links and refuses the whole write if a file does not exist at that
  commit or a line range runs past the end of the file.
- **Re-runs are incremental.** An item is re-audited only if a file its last audit read has
  changed since. Whole files are compared, not line ranges, so a change elsewhere in a file the
  verdict rests on is never skipped. `full` re-audits everything.
- **Read versus inferred.** Every step in the write-up was read in the code unless it is labeled
  inferred, and "the code can't settle it" is an allowed verdict.
- **It informs; it does not decide.** It never closes, drops, or files anything.

### Install

```
cp -r park-audit ~/.claude/skills/
cp park-audit/park-auditor.md ~/.claude/agents/
```

Then edit the CONFIG block at the top of `~/.claude/skills/park-audit/park_audit.py`: the local
repository, remote and base branch, your code host (`github`, `gitlab`, `bitbucket`, or `none`)
and repository URL, and your issue key and URL. Needs `/park` (it reads its parking lot) and
Python 3. To let auditors search your tracker, add its read-only search tools to the `tools:`
line in `park-auditor.md`.

## socratest

A quiz on a ticket before you test it.

Tickets are often written by people who know the product so well that they skip the basics:
what "pick" means, which link the ticket is about, what the button does to an order. `/socratest`
closes that gap before testing starts. Claude reads the ticket and the code under test, builds an
answer key silently, and then asks you five rounds of questions:

1. What is this ticket testing?
2. Where does it live in the app?
3. The domain terms it assumes
4. What could go wrong?
5. Exploratory test ideas beyond the ticket's checklist

```
/socratest SHOP-210
```

You answer first. Claude says what you got right, gives one hint toward the biggest gap, and
lets you try again; a second miss gets the full answer with its source. Every grade ends with
"How you could have found this yourself": the document section, the on-screen path, or the file
and the search that answers the round, so the next ticket needs the quiz less.

### Design choices

- **Try first, then check.** Attempting an answer before seeing it makes it stick.
- **One question at a time, and an unambiguous one.** Questions about behavior always say "before
  the fix" or "after the fix", since a question that fits both gets right answers graded wrong.
- **Grade only against sources.** Facts in the answer key are tagged with where they came from;
  anything inferred is offered as "probably", never graded.
- **Gaps are saved.** Terms go to a glossary, app facts to your project notes, and a short
  background brief to the run log.

### Install

```
cp -r socratest ~/.claude/skills/
```

Reading the ticket needs access to your issue tracker; without it, paste the ticket in. Reading
the code under test needs the repo checked out with the branch fetched.

## worst-case

A risk assessment for the test cases a run skipped.

A test run almost never covers everything: some cases need data nobody has, some need a person
or a system the tester cannot reach, and some were tried but proved nothing. The question that
decides whether the change ships is not "was everything tested" but "what is the worst that
happens if the untested part is wrong, who feels it, and is that worse than today."

```
/worst-case the three cases under Not exercised on SHOP-301, branch shop-301-pickup-tax
```

For each case, Claude answers six questions: the single worst outcome, with a number in it; who
feels it (the end user, the business, third parties) and how fast; whether that would be a
regression or the behavior that already existed; whether the case shares a code path with a step
that passed; what it would cost to close by hand and who can do it; and a recommendation (merge,
close by hand first, or hold). Every claim is labeled verified, with the file and line or the
passed step, or reasoned.

Before any of that, it sizes the work and lets you choose:

```
Case                                   To verify it needs                     Recommend
1 Gift card alone stays untaxed        one search in the changed file         read (1 min)
2 Held order with a back issue         same branch as the passed pickup step  reason from the pass
3 Shipping charge on an in-store order trace of who calls the tax calculator  wider read, or reason, labeled
4 Email tax line outside the home state not code: the tax service's settings  ask the owner; cannot verify here
```

You pick per case, or take the recommendations in one word. Nothing is read until you have.

The output comes in two sizes: a full walk-through in chat, for building the judgment, and a
condensed plain-text note sized for a ticket comment, in your words, posted nowhere unless you
say so. A quiz mode asks you the six questions first and then shows where Claude's answers
differ from yours.

### Design choices

- **Size first, then spend.** The triage table exists so you never find out twenty minutes in
  that a case could not be verified, or that a trivial one was not worth the read. A wider read
  than was sized gets stopped and reported, not finished.
- **Verified or reasoned, always labeled.** A skipped read looks the same as a verified one
  unless the label forces the difference.
- **Regression is the hinge.** A pre-existing shortfall the change can only improve is a
  different decision from a new branch nothing exercised; the skill always says which it is.
- **It recommends; it does not act.** "Close by hand first" is a recommendation. Running the
  test, fixing the code, or posting the note are separate decisions you make.

### Install

```
cp -r worst-case ~/.claude/skills/
```

The regression and code-path answers need the change to be reachable: a checked-out repo with
the branch fetched, or a diff. Reading the ticket needs access to your issue tracker. Without
them, those answers are labeled reasoned.

## License

MIT -- see [LICENSE](LICENSE).
