# GitHub Issue Management

## Overview

This project uses **GitHub Issues** for work tracking and **GitHub Actions** for CI/CD.

## Available Tools

You have access to GitHub via the **GitHub MCP server**. Use these tools:

| Tool | Purpose |
|------|---------|
| `mcp_github_list_issues` | List issues in a repo |
| `mcp_github_get_issue` | Get issue details |
| `mcp_github_create_issue` | Create new issue |
| `mcp_github_update_issue` | Update issue (labels, assignees, state) |
| `mcp_github_add_issue_comment` | Add comment to issue |
| `mcp_github_create_pull_request` | Create PR |
| `mcp_github_get_pull_request` | Get PR details |
| `mcp_github_search_issues` | Search issues/PRs |

**Prefer MCP tools over `gh` CLI** - they're more reliable and don't require shell access.

## Quick Reference

### CLI Commands (gh)

```bash
# List issues
gh issue list
gh issue list --assignee @me
gh issue list --label bug

# Create issue
gh issue create --title "Title" --body "Description"
gh issue create --title "Title" --label "enhancement" --assignee @me

# View/Edit
gh issue view 123
gh issue edit 123 --add-label "in-progress"
gh issue close 123 --comment "Completed in #PR"

# Link PR to issue
gh pr create --title "Fix #123: Description"  # Auto-links via "Fix #123"
```

### Issue Labels (Recommended)

| Label | Purpose |
|-------|---------|
| `bug` | Something isn't working |
| `enhancement` | New feature or improvement |
| `in-progress` | Currently being worked on |
| `blocked` | Waiting on something |
| `P0-critical` | Drop everything |
| `P1-high` | Do this sprint |
| `P2-medium` | Normal priority |
| `P3-low` | Nice to have |

---

## Workflows

### Starting Work

```bash
# Find something to work on
gh issue list --assignee @me
gh issue list --label "ready"

# Claim and start
gh issue edit 123 --add-label "in-progress" --add-assignee @me

# Create branch
git checkout -b fix/123-short-description
```

### Closing Work

Always close via PR when possible - use keywords in PR description:

| Keyword | Effect |
|---------|--------|
| `Fixes #123` | Closes issue when PR merges |
| `Closes #123` | Closes issue when PR merges |
| `Resolves #123` | Closes issue when PR merges |
| `Ref #123` | Links but doesn't close |

```bash
# Create PR that auto-closes issue
gh pr create --title "Fix login timeout" --body "Fixes #123

## Changes
- Updated timeout from 30s to 60s
- Added retry logic"
```

### Manual Close (no PR)

```bash
gh issue close 123 --comment "Completed: [summary of what was done]"
```

---

## GitHub Actions

Actions are configured in `.github/workflows/`. Common patterns:

```bash
# Check workflow runs
gh run list
gh run view 123456

# Re-run failed workflow
gh run rerun 123456

# View workflow logs
gh run view 123456 --log
```

---

## Beads Integration (Optional)

You can use Beads locally for detailed task breakdown while GitHub Issues tracks the main work items.

| Use GitHub Issues | Use Beads |
|-------------------|-----------|
| User-facing features | Implementation subtasks |
| Bug reports | Multi-session work breakdown |
| Team visibility | Dependencies between tasks |
| Sprint/milestone tracking | Context that survives sessions |

If using both, link them in the Beads description:
```bash
bd create "Implement auth flow" --body "GitHub Issue: #123"
```

---

## Common Mistakes to Avoid

1. Forgetting to link PRs to issues (use `Fixes #N` in PR body)
2. Not labeling issues with priority
3. Leaving issues assigned but not `in-progress`
4. Closing without documenting what was done
