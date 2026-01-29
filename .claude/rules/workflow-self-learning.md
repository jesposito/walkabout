# Self-Learning Skills Workflow

## Critical Rules

> **NEVER invent memories.** If recall finds nothing, say so and proceed with standard tools.

| Rule | Why It Matters |
|------|----------------|
| Check INDEX.md before non-trivial work | Avoid repeating past mistakes |
| Don't fabricate learnings | Invented memories cause wrong decisions |
| Record only non-obvious discoveries | Obvious things clutter the memory store |
| Never store secrets | Memory persists and may be shared |

---

## Overview

Self-learning skills is a persistent memory system. Use it to recall past learnings before work and record new discoveries after work.

| Location | Purpose |
|----------|---------|
| `.agent-skills/self-learning/v1/users/<user>/` | Storage directory |
| `.agent-skills/.../INDEX.md` | Human-readable dashboard |
| `.claude/skills/self-learning-skills/scripts/self_learning.py` | CLI tool |

---

## When to Use

| Timing | Action |
|--------|--------|
| **Before non-trivial work** | Recall relevant learnings from INDEX.md |
| **After completing work** | Record discoveries as Aha Cards |
| **Session end** | Review open recommendations |

---

## Pre-Work: Recall

Before starting any non-trivial task:

1. **Check INDEX.md** at `.agent-skills/self-learning/v1/users/<user>/INDEX.md`
2. **Search if needed** using `list --query "<keywords>"`
3. **Summarize** 3-7 actionable bullets relevant to current task

See: [code/workflow-self-learning/workflows.md](code/workflow-self-learning/workflows.md)

---

## Post-Work: Record

After completing work with discoveries, capture:

| Type | Count | Content |
|------|-------|---------|
| **Aha Cards** | 1-5 | Durable, reusable learnings |
| **Recommendations** | 1-5 | Actionable improvement suggestions |

**Required fields:**
- `title` - Clear, specific
- `primary_skill` - Use `unknown` if unsure
- `scope` - `project` or `portable`

See: [code/workflow-self-learning/workflows.md](code/workflow-self-learning/workflows.md)

---

## What to Record

### Good Aha Cards

| Type | Example |
|------|---------|
| Bug fix | "Beads sync fails if config.yaml has wrong repo ID - run `bd migrate --update-repo-id`" |
| Pattern | "GitHub PR descriptions support full markdown formatting" |
| Constraint | "bd edit opens $EDITOR which blocks agents - use `bd update --notes` instead" |
| Command | "Check beads health with `bd doctor` before debugging sync issues" |

### Not Worth Recording

- Obvious things (basic git commands, how to run tests)
- One-off fixes unlikely to recur
- Information already in official docs
- Secrets or sensitive data

---

## Scoping

| Scope | Meaning | Backport? |
|-------|---------|-----------|
| `project` | Specific to this repo | No |
| `portable` | Generally reusable | Yes |

**Writing portable learnings:**
- Replace repo-specific values with placeholders (`<repo-root>`, `<SERVICE>`)
- Prefer patterns over raw examples
- Avoid absolute paths
- Never include secrets

---

## Session End Checklist

- [ ] Record any new discoveries as Aha Cards
- [ ] Review open recommendations
- [ ] Mark completed recommendations as `done`

---

## Common Mistakes

| Mistake | Why It's Wrong |
|---------|----------------|
| Inventing memories | If recall finds nothing, say so - don't fabricate |
| Recording obvious things | Only record non-obvious discoveries |
| Skipping recall | Always check INDEX.md before non-trivial work |
| Recording secrets | Never store sensitive data |
| Dumping raw JSON | Summarize; point to INDEX.md for details |
