---
name: worst-case
description: Risk assessment for the test cases a run skipped or did not exercise. For each case it answers six questions (worst outcome, who feels it, regression or pre-existing, same code path as a passed step, cost to close by hand, recommendation), labels every claim verified or reasoned, and ends with a full walk-through plus a condensed note sized for a ticket comment. Sizes the work up front so the user picks what gets verified before anything expensive starts. Use when the user types /worst-case, or asks what the risk is of not testing something, or whether a change is safe to merge with cases untested.
argument-hint: "[the skipped cases, in your words] [ticket id] [branch or diff]"
---

# Worst case

A test run almost never covers everything. Some cases get skipped for lack of data, some need a
person or a system the tester cannot reach, and some were attempted but proved nothing. The
question that decides whether the change can ship is not "was everything tested" but "what is the
worst that happens if the untested part is wrong, who feels it, and is that worse than today."

This skill answers that question per case, with evidence, and in two sizes: a full walk-through
for the person learning to make the call, and a condensed note for the ticket.

Arguments given: `$ARGUMENTS`

## Inputs

Accept any of these, in any combination. Only the first is required.

- **The skipped cases, in the user's words.** Pasted from a results table, typed from memory, or
  "the ones under Not exercised in the results comment on the ticket". If no cases were given,
  ask for them as the only question this turn; do not go looking for them.
- **A tracker issue id**, if the user has one and Claude can reach the tracker. Read the issue
  and its test results; take the cases from there if the user pointed at them.
- **A pointer to the change**: a branch name, a commit range, or a diff. This is what makes the
  "regression" and "same code path" answers verifiable instead of reasoned. Without it, those
  answers are labeled reasoned.

Also use whatever the session already knows: a test run that just finished, a results table on
screen, a diff already read. Never spend effort gathering context the user did not ask for.

## Step 1: Restate the cases

List each case in one line, numbered, in the user's order. For each, say what it was meant to
guard: the behavior that would be wrong if the case failed. If a case is unclear, ask once; do
not guess what the user meant.

## Step 2: Choose the mode (one question)

Ask once with AskUserQuestion:

- **Quiz first.** For each case, the user answers the six questions in their own words before
  Claude does. Claude then gives its own assessment and names where the two differ. Slower; for
  someone building the judgment.
- **Assess only.** Claude produces the assessment; the user reads and challenges it.

Ask every run; do not remember the answer across runs.

## Step 3: Size the work before doing any of it

This step exists so nobody finds out twenty minutes in that a case could not be verified, or that
a trivial one was not worth the read. Before reading any code, print one table:

```
Case                              To verify it needs                       Recommend
1 <one line>                      one search in the changed file           read (1 min)
2 <one line>                      same branch as a passed step             reason from the pass
3 <one line>                      trace of who calls the changed method    wider read (5-10 min), or reason, labeled
4 <one line>                      not code: a setting in an outside system ask the owner; cannot verify here
5 <one line>                      nothing (a label typo)                   no read needed
```

The middle column is one sentence of sizing. Use these kinds, and no others:

- **local read**: the answer is in the changed file or one it names; minutes.
- **wider trace**: the answer depends on callers or data spread across the codebase; longer, and
  the kind of side quest that eats a session.
- **same branch as a passed step**: the case runs the same code as a step that passed with a
  different entry point; the pass is the evidence, no read needed.
- **not code**: the answer lives in configuration, an outside service, or a person's head.
- **nothing**: too small to need evidence; say so.

The last column is a phrase, not a sentence. Then ask with AskUserQuestion, one question per case
if there are four or fewer, otherwise one question offering "take the recommendations" / "pick
per case": read / reason only (labeled) / skip this case. Do not start any read until the user
has answered. Keep the table short; its job is an informed choice, not a report.

## Step 4: The six questions, per case

In quiz mode, put the six questions for ONE case in a message, let the user answer in words, then
give Claude's assessment of that case and name each place the answers differ and why. In assess
mode, go straight to the assessment. Either way, one case at a time, in the user's order.

1. **Worst outcome.** If this case is wrong, what is the single worst thing that happens? One
   concrete scenario with a number in it ("a $50 gift card rung up with $3.75 tax"), not a
   category ("tax is wrong").
2. **Who feels it, and how.** Three audiences, each answered even if the answer is "nothing":
   - the end user (customer, member, visitor): what they see, what they do about it;
   - the business (staff, owners, support): how and how fast they notice, what it costs them;
   - third parties (vendors, partners, payment or tax services, integrations): anything at all.
3. **Regression or pre-existing.** Would the failure be new behavior introduced by this change,
   or the behavior that already existed before it? This decides whether shipping makes anything
   worse. With a diff, cite the lines. Without one, label the answer reasoned.
4. **Same code path?** Does the case run through code that a passed step already exercised, with
   a different way in, or through a path nothing touched? A shared path inherits the pass; an
   untouched path does not.
5. **Cost to close by hand.** What it would take to test it now, how long, and who can do it:
   the user, an automated tester, a person with more access, the owner of an outside system.
6. **Recommendation.** One of: **merge** (the risk is bounded and not new), **close by hand first**
   (cheap to test and worth it), **hold** (new behavior with real exposure and no way to test
   here). One sentence of reason.

Evidence rules:

- Every factual claim is labeled **verified** (with the file and line, the passed step, or the
  record it came from) or **reasoned**. A reader must be able to tell which without asking.
- A read the user declined in Step 3 stays declined: answer reasoned, say so, move on.
- A read that turns into a wider trace than Step 3 sized is stopped, not finished: report what was
  found, label the rest reasoned, and let the user decide whether to continue.
- Do not fix, test, or file anything. "Close by hand first" is a recommendation; running it is a
  separate decision the user makes.

## Step 5: Output, two sizes

**The walk-through** (in chat): one block per case with the six answers, in plain words, every
term defined where it is used, no file or class names in the prose except as a citation after a
verified claim. Then a one-paragraph net: how many cases are pre-existing shortfalls the change can
only improve, how many are new branches, and the overall recommendation.

**The condensed note** (for the ticket): one short paragraph per case, three or four sentences,
in this order: what was skipped, the worst outcome, who feels it, regression or pre-existing, the
recommendation. End with one net sentence. Written in the user's first person if they will post
it. Plain text, no markdown, because many tracker editors paste markdown literally. ASCII only.

Show the condensed note in the last message of the turn with no tool call after it, so it
reaches the screen. Post it nowhere unless the user says to; if Claude posts it on the user's
behalf, add a closing line saying whose words they are.

## Worked example

A change made in-store pickup orders tax back issues at the store rate (they were untaxed; the
register already taxed them). The run passed every core step and left four cases:

```
Case                                   To verify it needs                     Recommend
1 Gift card alone stays untaxed        one search in the changed file         read (1 min)
2 Held order with a back issue         same branch as the passed pickup step  reason from the pass
3 Shipping charge on an in-store order trace of who calls the tax calculator  wider read, or reason, labeled
4 Email tax line outside the home state not code: the tax service's settings  ask the owner; cannot verify here
```

Condensed note after the reads the user chose:

```
Gift card alone. Every gift card line is marked non-taxable before the calculator looks at a tax
code, and the change did not touch that (verified, three builders). If it had, every gift card
would be taxed and staff would see it the same day. A regression if it happened; likelihood nil.

Held order with a back issue. Same calculator branch as the pickup step that passed. Worst case is
the old behavior: the back issues go untaxed and the store under-collects; nobody outside notices.
Pre-existing. Merge.

Shipping charge on an in-store order. The one new branch nothing exercised. It reaches only old
order displays and the audit export, not checkout. Worst case is a bogus balance due on an old
order's history page and a support email. Two reviewers read the branch. Merge.

Email tax line outside the home state. Both sides of the guard were seen in the run. Worst case is
the old behavior, a missing line while the total includes tax. Pre-existing. Needs a state where
tax is collected, which is a setting the owner controls. Merge; ask the owner.

Net: three pre-existing shortfalls the change can only improve, one new branch with no checkout
exposure. Moving to ready for merge.
```
