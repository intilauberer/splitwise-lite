# Contributing

The rules here exist so that reviews are fast and history stays readable.

## Branches

`main` is protected. No direct pushes, ever. Branch from an up-to-date `main`:

```
<type>/<issue-number>-<short-slug>
```

`type` is one of `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`.
Example: `feat/12-weighted-split`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <imperative summary, <=72 chars>

Why the change is needed. What the reader cannot infer from the diff.
Not a restatement of the diff itself.

Refs #12
```

A commit should build and pass tests on its own. If you find yourself writing
"and" in the summary, it is probably two commits.

## Pull requests

**Size is a feature.** Target under ~400 changed lines. Review quality falls off
a cliff past that, and the data on defect detection agrees. If a change is
genuinely large, split it into a stack: refactor first (no behaviour change),
then the behaviour change on top.

One PR = one reviewable idea. A PR that renames things *and* fixes a bug is two
PRs; the rename hides the bug.

Fill in the template honestly. The "Reviewer notes" section is the highest-value
part: it tells the reviewer where to spend their attention.

## Definition of done

- [ ] CI green: `ruff check .`, `ruff format --check .`, `mypy`, `pytest --cov`
- [ ] New logic has tests at the right level (see `tests/README.md`)
- [ ] Coverage does not drop below the 90% gate
- [ ] PR description explains *why*, not just *what*
- [ ] Branch deleted after squash-merge

## Reviewing

Reviews use [conventional comments](https://conventionalcomments.org/) so that
severity is unambiguous:

- **blocking:** must change before merge
- **suggestion:** I would do it this way; your call
- **question:** I do not understand this yet
- **nit:** cosmetic, never blocking
- **praise:** say this out loud when it is deserved

Approve with unresolved nits. Block only on correctness, security, or a
maintainability cost the author has not weighed.
