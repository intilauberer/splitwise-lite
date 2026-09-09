---
name: open-pr
description: Turn the current branch into a properly scoped pull request against main - checks size and scope, runs the full local gate, writes the description from the actual diff, and opens it as a draft. Use when the user says "open a PR", "raise a PR", "ship this branch", or when work on a feature branch looks finished.
---

# Opening a pull request

## 1. Refuse to open a bad PR

Before anything else, run:

```bash
git fetch origin main
git diff --stat origin/main...HEAD
```

Stop and tell the user, rather than opening the PR, if:

- **It exceeds ~400 changed lines** (excluding lockfiles, generated code, and
  pure moves). Propose a concrete split: usually the mechanical refactor first
  as its own PR, then the behaviour change on top of it.
- **It contains more than one reviewable idea.** A rename plus a bug fix is two
  PRs — the rename hides the fix. So is "feature + unrelated drive-by cleanup".
- **It has no tests** and touches behaviour, not just docs or config.
- **The branch is behind `origin/main`.** Rebase first: `git rebase origin/main`.

Say *which* rule tripped and what the split should be. Do not just proceed.

## 2. Run the gate locally

Never make CI find something the author could have. Run and fix:

```bash
ruff check . && ruff format --check . && mypy && pytest --cov
```

## 3. Write the description from the diff, not from memory

Read the actual diff. Fill `.github/pull_request_template.md`:

- **What & why** — the problem, not the patch. If the "why" is only restating
  the "what" ("adds a weighted split because we needed a weighted split"), you
  have not found the why yet: ask what breaks without it.
- **How** — the approach, plus one alternative you rejected and the reason.
- **Testing** — name the specific cases: "covers the remainder path where the
  amount does not divide evenly", not "added tests". State what is *not*
  covered and why.
- **Risk & rollout** — blast radius, whether it is safely revertible.
- **Reviewer notes** — the highest-value section. Point at the part you are
  least sure of. This is what makes a reviewer fast.

Title is the conventional-commit summary: `feat(money): allocate by weight`.

## 4. Open it as a draft

```bash
gh pr create --draft --fill-first --base main
```

Then mark ready once CI is green: `gh pr ready`. Opening as draft means a red
first run does not burn a reviewer's attention.

## 5. Report back

Give the user the PR URL, the changed-line count, and the one thing you would
look at hardest if you were reviewing it.
