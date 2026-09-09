---
name: self-review
description: Review a diff or PR the way a senior reviewer would - correctness first, then design, then style - and report findings as conventional comments with explicit severity. Use when the user asks to review code, review their own PR, or check a branch before requesting review.
---

# Reviewing code

## Order matters

Review in this order and stop escalating once you find something blocking —
there is no point debating a variable name in a function that is wrong.

1. **Correctness.** Does it do what the description claims? Off-by-one,
   rounding, empty/null input, boundary values, error paths, concurrency,
   partial failure. For anything touching money or time, assume it is wrong
   until you have traced one concrete example by hand.
2. **Tests.** Do the tests *actually pin the behaviour*, or do they restate the
   implementation? Would they fail if you inverted a condition in the code? If
   not, they are decoration. Check the edge cases are tested, not just the
   happy path.
3. **Security & data.** Injection, authz on the new endpoint, secrets in the
   diff, PII in logs, unbounded input.
4. **Design.** Is this in the right layer? Does it leak a domain concept into
   the transport layer, or vice versa? Will the next change be easy?
5. **Readability.** Naming, dead code, comments explaining *why* not *what*.
6. **Style.** Only if the linter does not already catch it. If you are typing a
   style comment a tool could make, the fix is to configure the tool.

## Say how much you mean it

Prefix every comment ([conventional comments](https://conventionalcomments.org/)):

- **blocking:** correctness, security, or a maintainability cost the author
  clearly has not weighed. Must change before merge.
- **suggestion:** you would do it differently. Author decides. Not a gate.
- **question:** you genuinely do not understand. Ask before assuming a bug —
  half of these turn out to be the reviewer being wrong.
- **nit:** cosmetic. Explicitly non-blocking. Use sparingly; a wall of nits
  drowns the one comment that mattered.
- **praise:** name the specific good decision. This is not filler — it tells the
  author which instincts to keep.

## Write comments that can be acted on

A good comment has: what is wrong, why it matters, and a concrete suggestion.

> **blocking:** `allocate()` hands every remainder cent to index 0 when all
> ratios are equal, so the same person always overpays. Over a year of weekly
> splits that is a real drift. Sort by remainder descending and break ties by
> index — and add a test asserting the shares sum back to the total.

Not: "this looks wrong".

## Reviewing your own PR

Do this before requesting review — it is the single highest-leverage habit.

Read the diff on GitHub, not in your editor. The different rendering breaks the
familiarity that makes you skim. Leave real comments on your own PR where you
made a judgement call; it pre-answers the reviewer's questions and shows your
reasoning.

Ask specifically: *if this is on fire at 3am, what will the cause have been?*

## Reporting

Group findings by severity, most severe first. State the file and line. If
nothing is blocking, say so plainly and approve — a review that finds nothing is
a legitimate outcome, and manufacturing a nit to look thorough wastes everyone's
time.
