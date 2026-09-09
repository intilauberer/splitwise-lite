# Claude Code Skills in this repo

A **Skill** is a folder with a `SKILL.md`: YAML frontmatter (`name`,
`description`) plus instructions in Markdown. It is a reusable prompt that lives
in the repo, versioned next to the code it describes.

The `description` is the important half. Claude reads only the name and
description until a skill is needed — that line is what decides whether the
skill fires. Write it as *when to use this*, not *what this is*.

```
.claude/skills/
  open-pr/SKILL.md      turning a branch into a well-scoped PR
  self-review/SKILL.md  reviewing a diff like a senior engineer
```

Invoke explicitly with `/open-pr`, or just describe the task and let the
description match.

## Why a team keeps these in the repo

The alternative to a skill is a convention that lives in someone's head, gets
explained in code review, and decays. A skill is the same knowledge, checked in:

- it is **reviewed** — changing how the team opens PRs is itself a PR
- it is **versioned** — you can see when a rule was added and read the reasoning
- it is **shared** — a new hire gets the team's review standard on day one
- it **degrades gracefully** — it is Markdown, so a human can just read it

This is the honest answer to "how do skills fit a modern GitHub flow": they turn
tacit process knowledge into a reviewable artifact, same as CI config did for
build steps and CODEOWNERS did for review routing.

## Where skills can live

| Scope | Location | Applies to |
|---|---|---|
| Project | `.claude/skills/` (committed) | everyone on the repo |
| Personal | `~/.claude/skills/` | just you, every repo |
| Plugin | shipped in a plugin | anyone who installs it |

Related, and often confused with skills:

- **Slash commands** (`.claude/commands/`) — a single prompt, invoked by name.
  Simpler; no progressive disclosure, no bundled files.
- **Subagents** (`.claude/agents/`) — a *separate* context window with its own
  tools. Use when you want isolation (a long search that would flood the main
  context), not just instructions.
- **Hooks** (`settings.json`) — shell commands the harness runs deterministically
  on events. A hook always runs; a skill runs when the model judges it relevant.
  Use a hook for "always format on write", a skill for "review this well".
- **`CLAUDE.md`** — always in context, so keep it short. Anything conditional
  belongs in a skill instead.
