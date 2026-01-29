# Versioning Commands

## Commit the CHANGELOG

```bash
git add CHANGELOG.md
git commit -m "Prepare release v1.2.0"
```

## Create Annotated Tag

```bash
git tag -a v1.2.0 -m "v1.2.0 - Brief description

- Key change 1
- Key change 2"
```

## Push Commit and Tag

```bash
git push && git push --tags
```

## Quick Reference

```bash
# View all tags
git tag -l

# View tag details
git show v1.0.0

# Delete a tag (local)
git tag -d v1.0.0

# Delete a tag (remote)
git push --delete origin v1.0.0

# List commits since last tag
git log $(git describe --tags --abbrev=0)..HEAD --oneline
```
