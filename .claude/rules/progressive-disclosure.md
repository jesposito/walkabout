# Progressive Disclosure for Rules

## Overview

Rules follow a progressive disclosure pattern: main rule files are concise reference guides, with detailed code examples in separate files. This keeps context small and lets Claude load only what's needed.

**Two key principles:**
1. **Vertical ordering** - Critical rules first, edge cases last
2. **Horizontal splitting** - Concise main file, detailed code files

---

## Content Ordering

Order content by importance - what breaks things goes first, rare edge cases go last.

| Position | Content Type | Example |
|----------|--------------|---------|
| **Top** | Critical rules, things that break if wrong | "NEVER start coding without setting status" |
| **Upper** | Core workflow, common operations | Creating items, updating status |
| **Middle** | Reference tables, quick lookup | Priority scale, field descriptions |
| **Lower** | Less common operations | Dependencies, parent items |
| **Bottom** | Edge cases, error recovery | Sync failures, reopening closed items |

### Standard Section Order

```
1. Critical Rules (Read First)
2. Overview / When to Use
3. Quick Reference (tables)
4. Common Workflows
5. Creating / Updating
6. Closing / Completing
7. Edge Cases and Error Recovery
8. Common Mistakes to Avoid
```

---

## Structure

```
.claude/rules/
├── my-rule.md                    # Concise rule (tables, key points)
└── code/
    └── my-rule/
        └── workflows.md          # Detailed commands and examples
```

---

## Main Rule File Guidelines

| Do | Don't |
|----|-------|
| Put critical rules at the very top | Bury important rules in later sections |
| Put edge cases at the bottom | Lead with error handling |
| Use tables for quick reference | Include multi-line code blocks |
| Keep sections brief (3-5 bullets) | Duplicate information across sections |
| Reference code files with `See:` links | Put JSON payloads inline |

### Ideal Section Pattern

```markdown
## Section Name

Brief description (1-2 sentences).

| Column 1 | Column 2 |
|----------|----------|
| Item | Description |

See: [code/my-rule/workflows.md](code/my-rule/workflows.md)
```

---

## Code File Guidelines

| Include | Organize By |
|---------|-------------|
| Full command examples | Workflow phase (pre-work, during, post-work) |
| JSON payload samples | Operation type (create, update, close) |
| Multi-step procedures | Common scenarios |
| Edge case handling | Complexity (basic → advanced) |

### Code File Structure

```markdown
# Topic Commands

## Basic Operations

\`\`\`bash
command --example
\`\`\`

## Advanced Operations

\`\`\`bash
command --with --many --flags
\`\`\`

## Payload Formats

\`\`\`json
{ "example": "payload" }
\`\`\`
```

---

## Reference Pattern

In the main rule, link to code files:

```markdown
See: [code/topic/workflows.md](code/topic/workflows.md)
```

Place the `See:` link at the end of each section that has detailed examples.

---

## Examples

### Good Main Rule Section

```markdown
## Creating Items

Create items with required fields: title, type, priority.

| Field | Required | Default |
|-------|----------|---------|
| `title` | Yes | - |
| `type` | Yes | - |
| `priority` | No | 2 |

See: [code/tracking-beads/creating-items.md](code/tracking-beads/creating-items.md)
```

### Bad Main Rule Section

```markdown
## Creating Items

To create an item, run:

\`\`\`bash
bd create --title "My item" --type task --priority 2
\`\`\`

You can also create with a parent:

\`\`\`bash
bd create --title "Child item" --type task --parent devenv-001
\`\`\`

For bugs, use priority 1:

\`\`\`bash
bd create --title "Bug" --type bug --priority 1
\`\`\`
```

---

## When to Split

| Split to code file | Keep inline |
|--------------------|-------------|
| 3+ command examples | Single short command |
| Multi-line JSON | Simple key-value reference |
| Step-by-step procedures | Checklist items |
| Platform-specific variants | Universal one-liners |

---

## Existing Code Directories

| Directory | Contents |
|-----------|----------|
| `code/tracking-github/` | GitHub CLI and MCP commands |
| `code/tracking-beads/` | Beads workflows, dependencies, edge cases |
| `code/style-csharp/` | C# code patterns |
| `code/workflow-implementation/` | Implementation workflow commands |
| `code/workflow-planning/` | Planning workflow commands |
| `code/workflow-self-learning/` | Self-learning CLI and payloads |
| `code/versioning/` | Git tag and release commands |
