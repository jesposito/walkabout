# Versioning

## Critical Rules

> **This project uses [Semantic Versioning](https://semver.org/).** Every release must have a git tag and CHANGELOG entry. GitHub releases are created automatically when tags are pushed.

| Version Part | When to Bump | Example |
|--------------|--------------|---------|
| **MAJOR** (X.0.0) | Breaking changes to workflows or rules | Removing a required rule, changing command syntax |
| **MINOR** (0.X.0) | New features, new rules, backwards-compatible | Adding a new rule file, new workflow |
| **PATCH** (0.0.X) | Bug fixes, documentation improvements | Fixing typos, clarifying rules |

---

## Release Process

See: [code/versioning/release.md](code/versioning/release.md)

### 1. Update CHANGELOG.md

Move items from `[Unreleased]` to a new version section:

```markdown
## [Unreleased]

## [1.2.0] - 2026-01-22

### Added
- New feature X

### Changed
- Updated rule Y

### Fixed
- Bug in Z
```

### 2. Commit the CHANGELOG

### 3. Create Annotated Tag

### 4. Push Commit and Tag

### 5. Update CHANGELOG Links

Add the new version to the comparison links at the bottom:

```markdown
[Unreleased]: https://github.com/owner/repo/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/owner/repo/releases/tag/v1.2.0
[1.1.0]: https://github.com/owner/repo/releases/tag/v1.1.0
```

---

## CHANGELOG Format

Follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/):

| Section | Use For |
|---------|---------|
| `Added` | New features, new rules |
| `Changed` | Changes to existing functionality |
| `Deprecated` | Features to be removed in future |
| `Removed` | Removed features |
| `Fixed` | Bug fixes |
| `Security` | Security-related changes |

---

## When NOT to Create a Release

- Work-in-progress changes (keep in `[Unreleased]`)
- Changes that only affect development tooling
- Commits that will be amended or rebased

---

## Common Mistakes to Avoid

1. Forgetting to update CHANGELOG.md before tagging
2. Using lightweight tags instead of annotated tags (`-a` flag)
3. Not pushing tags (`git push --tags`)
4. Bumping MAJOR for non-breaking changes
5. Forgetting to update the comparison links in CHANGELOG.md
