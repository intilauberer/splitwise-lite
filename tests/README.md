# Testing strategy

Tests are grouped by *what they are allowed to touch*, not by what they cover.
That is the distinction that actually matters: it determines speed, flakiness,
and what a failure tells you.

```
tests/
  unit/          pure functions, no I/O          ~ms        run on every save
  integration/   real collaborator (db, fs)      ~100ms     run on every commit
  api/           HTTP surface, wired app         ~1s        run in CI
```

## Unit

One unit of behaviour, no network, no disk, no clock, no randomness. If it needs
a mock to run at all, the design is probably wrong — prefer passing a value in
over patching a global.

Fast enough that you run them constantly. They are where edge cases live:
rounding, empty input, boundary conditions, error paths.

## Integration

Two or more real components together, typically code plus a real database or a
real filesystem. Use a *real* SQLite/Postgres, not a mock — the point is to catch
the things a mock cannot: schema drift, transaction semantics, constraint
violations, serialisation.

Rule of thumb: mock things you own, use the real thing for what you don't
control but *can* run locally. Never assert against a mock of the thing under
test.

## API / contract

Drive the app through its public HTTP surface with a test client. Asserts the
contract other teams depend on: status codes, payload shape, validation errors,
auth. These are the tests that catch "we renamed a field and broke mobile."

## The ones this repo does not have (and what they'd be)

- **End-to-end**: the whole system deployed, driven like a user (Playwright,
  Cypress). Slow, flaky, expensive. Keep a handful covering critical journeys —
  signup, checkout — not a full regression suite.
- **Contract tests (Pact)**: consumer and producer verify a shared contract
  independently, so you catch a breaking change without deploying both.
- **Property-based** (Hypothesis): assert invariants over generated inputs.
  `allocate()` is a perfect candidate: *the shares always sum to the total*, for
  any amount and any ratios.
- **Snapshot/golden**: freeze a rendered output and diff it. Cheap, but rots.
- **Load/performance**: k6, Locust. Assert p99 latency under a target RPS.
- **Mutation testing** (mutmut, cosmic-ray): flips your code and checks whether a
  test fails. Measures whether coverage is *real*. 90% line coverage with a weak
  assertion set scores badly here — which is the point.
- **Smoke tests post-deploy**: a few assertions against production after a
  release, wired to auto-rollback.

## What the interviewer is actually asking

"What kinds of testing do you use?" is a proxy for three things:

1. **Do you know the trade-off?** Fast/narrow catches logic bugs cheaply;
   slow/broad catches wiring bugs expensively. You want a lot of the first and a
   few of the second — the pyramid. Invert it and CI takes 40 minutes and nobody
   trusts it.
2. **Do you know what a test is for?** A test is a design tool and a
   regression net, not a coverage number. Coverage tells you what was *executed*,
   not what was *verified*.
3. **Do you know when not to test?** Don't test the framework. Don't test
   getters. Don't write a test that restates the implementation — it will need
   changing every time you refactor, and it will never catch a bug.

## Running

```bash
pytest                       # everything
pytest -m unit               # fast loop
pytest -m "not api"          # skip the slow tier
pytest --cov                 # with the 90% gate
```
