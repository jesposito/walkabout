# Self-Learning Skills Commands

## Pre-Work: Recall

```bash
# Check INDEX.md directly
cat .agent-skills/self-learning/v1/users/<user>/INDEX.md

# Search by keyword
python .claude/skills/self-learning-skills/scripts/self_learning.py list --query "<keywords>"

# Search with filters
python .claude/skills/self-learning-skills/scripts/self_learning.py list --query "auth" --skill "security"
```

## Post-Work: Record

```bash
# Record from JSON file
python .claude/skills/self-learning-skills/scripts/self_learning.py record --json payload.json

# Mark existing learnings as used
python .claude/skills/self-learning-skills/scripts/self_learning.py use --aha aha_123,aha_456

# Mark recommendations as used
python .claude/skills/self-learning-skills/scripts/self_learning.py use --rec rec_123
```

## Review Commands

```bash
# Recent learnings (last 7 days)
python .claude/skills/self-learning-skills/scripts/self_learning.py review --days 7

# Portable learnings (backport candidates)
python .claude/skills/self-learning-skills/scripts/self_learning.py review --scope portable --days 30

# Filter by skill
python .claude/skills/self-learning-skills/scripts/self_learning.py review --skill "beads" --days 30

# JSON output
python .claude/skills/self-learning-skills/scripts/self_learning.py review --days 7 --format json
```

## Recommendation Status

```bash
# Mark as in progress
python .claude/skills/self-learning-skills/scripts/self_learning.py rec-status \
  --id rec_123 \
  --status in_progress \
  --note "Working on this"

# Mark as done and portable
python .claude/skills/self-learning-skills/scripts/self_learning.py rec-status \
  --id rec_123 \
  --status done \
  --scope portable \
  --note "Generalized for reuse"
```

## Maintenance

```bash
# Repair/normalize storage (dry run)
python .claude/skills/self-learning-skills/scripts/self_learning.py repair

# Apply fixes
python .claude/skills/self-learning-skills/scripts/self_learning.py repair --apply
```

## Payload Formats

### Minimal Aha Card

```json
{
  "aha_cards": [
    {
      "title": "Clear, specific title",
      "primary_skill": "beads",
      "scope": "project",
      "summary": "What was learned",
      "steps": ["Step 1", "Step 2"],
      "tags": ["tag1", "tag2"]
    }
  ]
}
```

### Minimal Recommendation

```json
{
  "recommendations": [
    {
      "title": "What to improve",
      "primary_skill": "unknown",
      "scope": "project",
      "description": "Why and how to improve it"
    }
  ]
}
```

### Combined Payload with Usage Tracking

```json
{
  "aha_cards": [
    {
      "title": "Learning title",
      "primary_skill": "beads",
      "scope": "portable",
      "summary": "What was learned",
      "steps": ["Step 1", "Step 2"],
      "tags": ["sync", "workflow"]
    }
  ],
  "recommendations": [
    {
      "title": "Improvement suggestion",
      "primary_skill": "beads",
      "scope": "project",
      "description": "Details"
    }
  ],
  "used": {
    "aha_ids": ["aha_existing_123"],
    "rec_ids": ["rec_existing_456"]
  }
}
```
