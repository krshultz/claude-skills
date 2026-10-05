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

A parked entry looks like this (one line in `~/.claude/parking-lot.md`):

```
- [ ] 2026-10-05 | BUG | "The expired coupon still applied -- total dropped by 10%." | during: SHOP-142 [Coupon codes at checkout], edge case E2 | doing: applying a second coupon to check that only one is allowed | page: /cart | test data: coupon SAVE10 expired 2026-10-04; cart has item 1017, qty 2 | evidence: tester's screenshot 3 -- cart shows "SAVE10 applied" | run log: shop-142-test-run.md, step E2
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

## License

MIT -- see [LICENSE](LICENSE).
