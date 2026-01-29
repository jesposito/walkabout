# Planning Workflow

## Critical Rules

**STOP** - Before doing anything else:

1. **NEVER create items before plan approval** - Use `ExitPlanMode` first, wait for user approval
2. **ALWAYS ask plan type first** - Master Plan or Feature Plan?
3. **For Feature Plans**: Get the feature ID before entering planning mode
4. **For Master Plans**: Ask if there's a related GitHub Issue/milestone to link
5. **Every feature MUST have a research task** - Named `"Research: <feature title>"`

## Quick Reference

| Plan Type | Creates | Use When |
|-----------|---------|----------|
| **Master Plan** | Epic + Features + Research Tasks | Starting new major work |
| **Feature Plan** | Tasks (under a feature) | Implementing a specific feature |

---

## Master Plan Workflow

See: [code/workflow-planning/workflows.md](code/workflow-planning/workflows.md)

### Step-by-Step

1. User runs `/plan-new`, selects Master Plan
2. Enter planning mode
3. Explore codebase, review existing Beads items
4. **Ask user about related GitHub Issue/milestone** (existing or create new)
5. Design the plan with acceptance criteria
6. Exit planning mode for approval
7. After approval, create items

### Plan File Structure

```markdown
# Master Plan: [Epic Title]

## Overview
[Brief description of the epic scope]

## GitHub
- Issue/Milestone: [existing #N or "to be created"]

## Acceptance Criteria
- [ ] Criteria 1
- [ ] Criteria 2

## Features

### Feature 1: [Title]
- **Priority**: P2
- **Description**: [What this feature delivers]
- **Dependencies**: [None or list of other features]
```

---

## Feature Plan Workflow

### Step-by-Step

1. User runs `/plan-new`, selects Feature Plan
2. Ask for feature ID
3. Enter planning mode
4. Review feature with `bd show`, check for research task
5. **If research exists**: Read research findings, verify feature description references them (add `## Research` section if missing)
6. Explore relevant code, identify files to change
7. Design task breakdown
8. Exit planning mode for approval
9. After approval, create tasks

### Plan File Structure

```markdown
# Feature Plan: [Feature Title]

## Feature Context
- **Beads ID**: [feature-id]
- **GitHub Issue**: [#N or "not linked"]
- **Parent Epic**: [epic-id]
- **Research**: [path to research doc, or "N/A" if no research task]

## Implementation Tasks

### Task 1: [Title]
- **Priority**: P2
- **Description**: [What this task accomplishes]
- **Files**: [Expected files to create/modify]
- **Dependencies**: [None or list of other tasks]

## Testing Approach
[How the feature will be tested]

## Technical Notes
[Any implementation considerations]
```

---

## Research Tasks

**Purpose**: Explore before implementing:
- Relevant code areas in the codebase
- Files that will need to be created/modified
- Technical constraints and dependencies
- Implementation options and approaches
- Best practices and patterns
- OSS libraries, tooling, or techniques

**Naming**: `"Research: <feature title>"`

**Priority**: Same as parent feature

**Output Location**: `docs/research/<issue-id>-<slug>.md`

**Usage**: Research is optional - it can inform the Feature Plan but the plan can proceed if scope is already well understood.

**IMPORTANT**: When research is complete, update the parent feature description to reference the findings:
```markdown
## Research
See: docs/research/<issue-id>-<research-slug>.md
```
This ensures traceability between research and implementation.

---

## Workflow Diagram

```
User runs /plan-new
    |
    v
Ask: Master Plan or Feature Plan?
    |
    +-> Master Plan
    |       |
    |       v
    |   EnterPlanMode
    |       |
    |       +-> Explore codebase
    |       +-> Ask about GitHub Issue/milestone
    |       +-> Design epic + features
    |       |
    |       v
    |   ExitPlanMode (approval)
    |       |
    |       v
    |   Create Epic + Features + Research Tasks
    |   (+ GitHub Issue if linked)
    |
    +-> Feature Plan
            |
            v
        Ask: Feature ID?
            |
            v
        EnterPlanMode
            |
            +-> Review feature (bd show)
            +-> Explore implementation areas
            +-> Design task breakdown
            |
            v
        ExitPlanMode (approval)
            |
            v
        Create Tasks
        (link to GitHub Issue if applicable)
```

---

## Common Mistakes to Avoid

1. Starting to plan without asking plan type first
2. Starting Feature Plan without getting feature ID
3. Forgetting to check for GitHub Issue links before creating items
4. Creating items before plan approval (ExitPlanMode)
5. Skipping acceptance criteria for Master Plans
6. Not asking about existing GitHub Issue/milestone for Master Plans
7. **Not linking completed research to feature** - When research task is closed, update feature description with `## Research` section pointing to findings
