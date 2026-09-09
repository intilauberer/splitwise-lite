# splitwise-lite

A small expense-splitting service. Its real purpose is to be a realistic,
well-run repository: protected `main`, required checks, reviewed PRs, and a
testing strategy that goes deeper than "we have tests."

## What it does

Track shared expenses in a group and work out who owes whom, with exact money
arithmetic (integer cents — never floats) and a settlement step that minimises
the number of transfers.

## Quick start

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows/Git Bash; use bin/activate on POSIX
pip install -e ".[dev]"

ruff check . && ruff format --check . && mypy && pytest --cov
```

## Layout

```
app/
  money.py        exact monetary values and allocation
tests/
  unit/           pure logic
  integration/    real collaborators
  api/            HTTP contract
.github/
  workflows/ci.yml
```

## How we work

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — branches, commits, PR size, review conventions
- [`tests/README.md`](tests/README.md) — what each test tier is for and why

Every change reaches `main` through a reviewed pull request with green CI.
