# Beads Work Item Management

## Critical Rules (Read First)

**The one thing that breaks everything:** Beads data lives in your git repo. If you don't sync before ending a session, you lose work or create merge conflicts.

```bash
bd sync --from-main  # Always run before ending session
```

### The Three Unbreakable Rules

1. **Always sync before session end** - `bd sync --from-main` prevents merge conflicts
2. **Always document closing** - Never close without listing files/tests changed
3. **Always set status before working** - Set to `in_progress` before starting work

### When to Use Beads vs GitHub Issues

| Use Beads | Use GitHub Issues |
|-----------|-------------------|
| Implementation details and subtasks | User-facing features and bugs |
| Multi-session coding work | Team visibility and milestones |
| Work with dependencies/blockers | External contributor issues |
| Discovered work during implementation | PR-linked work items |
| Context that must survive compaction | Public issue tracking |

**Rule of thumb**: GitHub Issues tracks *what* needs to be done (features/bugs). Beads tracks *how* you're doing it (implementation tasks).

### Linking to GitHub Issues

When a Beads item relates to a GitHub Issue, include the link:
```bash
bd create "Implement auth flow" --body "GitHub Issue: #123"
```

### When to Use Beads vs TodoWrite

| Use Beads | Use TodoWrite |
|-----------|---------------|
| Multi-session work | Single-session tasks |
| Has dependencies/blockers | Simple linear steps |
| Discovered work needing tracking | Execution checklist |
| Context that must survive compaction | Temporary progress tracking |

**When in doubt, use Beads** - persistence you don't need beats lost context.

---

## Initialization (New Projects)

```bash
bd init --prefix devenv --quiet  # Non-interactive with custom prefix
```

| Option | Purpose |
|--------|---------|
| `--prefix <name>` | Set memorable issue prefix (e.g., `devenv-001`) |
| `--contributor` | Fork workflow (routes issues to separate repo) |
| `--team` | Branch workflow for team collaboration |
| `--branch beads-sync` | Protected main branch workflow |
| `--quiet` | Non-interactive mode |

---

## Maintenance

### Handling AGENTS.md

Beads auto-generates `AGENTS.md` with command reference. When this file exists:

1. **Compare** AGENTS.md commands against this rule file
2. **Update** this rule if AGENTS.md has newer/better command patterns
3. **Delete** AGENTS.md after evaluation (our rules are the source of truth)

This ensures beads upgrades don't introduce command changes we miss.

---

## Quick Reference

### Priority Scale

| Priority | Meaning | Use For |
|----------|---------|---------|
| 0 (P0) | Critical | Blocking all other work |
| 1 (P1) | High | Must complete this session |
| 2 (P2) | Medium | Normal priority (default) |
| 3 (P3) | Low | Nice to have |
| 4 (P4) | Backlog | Future consideration |

### Issue Types

| Type | Use For |
|------|---------|
| `task` | Implementation work, refactoring, research |
| `bug` | Defects found during development |
| `feature` | New functionality (or link to GitHub Issue) |
| `epic` | Group of related tasks (use sparingly) |

### Issue Lifecycle

```
open  ──▶  in_progress  ──▶  closed
  │                            ▲
  └────────────────────────────┘
        (can close directly)
```

---

## Common Workflows

See: [code/tracking-beads/workflows.md](code/tracking-beads/workflows.md)

### Starting Work on an Item

**Pre-Work Checklist:**
- [ ] Item has required fields: title, type, priority
- [ ] Item is not blocked: `bd show <id>` shows no blockers
- [ ] GitHub Issue link is noted (if related)
- [ ] You understand the scope

### Closing an Item

**Required completion details:**
- Summary of work completed
- Files created, updated, removed (lists)
- Tests created, updated, removed (lists)

### Priority Scale

**Priority Rules:**
- Bugs should typically be P1 or higher (P0 if blocking)
- New items default to P2 unless urgency is known
- Document reason when changing priority

---

## Creating Items

See: [code/tracking-beads/creating-items.md](code/tracking-beads/creating-items.md)

### Key Rules

- **Epics**: Ask if user has existing GitHub Issue/milestone to link
- **Features**: Can ONLY be created under an existing epic
- **Features**: MUST have a research task
- **Tasks under features**: Link to GitHub Issue if one exists
- **Bugs**: Default to P1 priority

---

## Dependencies

See: [code/tracking-beads/dependencies.md](code/tracking-beads/dependencies.md)

**Best Practices:**
- Create dependencies when discovering work that must happen first
- Don't create circular dependencies
- Close blocking issues before dependent issues

### Closing Parent Items (Epics/Features)

Only close when ALL child items are complete.

**Parent Completion Checklist:**
- [ ] All child items are closed
- [ ] No open dependencies on child items
- [ ] Acceptance criteria verified (for epics/stories)
- [ ] GitHub Issue closed if linked (use `Fixes #N` in PR)
- [ ] Beads item closed with child item references

---

## Edge Cases and Error Recovery

See: [code/tracking-beads/edge-cases.md](code/tracking-beads/edge-cases.md)

| Situation | Action |
|-----------|--------|
| Partial completion | Document progress in notes, keep `in_progress` |
| Blocked by another item | Add dependency, document blocker |
| External blocker | Create placeholder item, add dependency |
| Reopen closed item | Set status to `open`, document reason |
| Cancel item | Close with "CANCELLED:" reason |
| API failure | Document failure, retry manually |
| Out of sync | GitHub Issues is source of truth for linked items |
| Missing link | Search GitHub Issues, add link if found |
| Orphaned item | Remove dead link from description |
| Repo ID mismatch | `bd migrate --update-repo-id` |

---

## Common Mistakes to Avoid

1. Creating issues without priority
2. Leaving issues in `in_progress` across sessions
3. Not syncing before ending session (`bd sync --from-main`)
4. Creating circular dependencies
5. Forgetting to link related GitHub Issues in Beads description
