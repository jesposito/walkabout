# Dev Environment Settings

## Overview

This environment uses GitHub for issue tracking and CI/CD. Settings are minimal.

## GitHub Configuration

GitHub access is configured via:

1. **GitHub CLI** (`gh`) - Already authenticated via `gh auth login`
2. **GitHub MCP Server** - Configured in `~/.claude.json` with your PAT

No additional settings files are required for GitHub workflows.

## User Settings (Optional)

If you need project-specific user settings, create `.devenv/settings.local.json`:

```json
{
  "user": {
    "email": "user@example.com"
  }
}
```

## Token Substitution

When generating commands, these tokens can be used:

| Token | Source |
|-------|--------|
| `<user-email>` | `settings.local.json` → `user.email` |
| `<github-repo>` | Current git remote (auto-detected) |

## Auto-Detection

The environment auto-detects:
- **GitHub repo** from `git remote get-url origin`
- **Current branch** from `git branch --show-current`
- **User info** from `gh api user`

## Missing Settings

If user settings are needed but not configured:

```
User settings not found. To configure:

1. Create .devenv/settings.local.json with your email
2. Re-run the command

This is optional - most workflows work without it.
```
