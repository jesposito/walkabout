# Implementation Workflow

## Critical Rules (Read First)

**The #1 rule that breaks everything if wrong:**

> **NEVER start coding without setting status to `in_progress`** - on the item AND all its parents (Feature, Epic). This is the most common cause of orphaned work and lost context.

### Absolute Requirements

| Requirement | Why It Matters |
|-------------|----------------|
| Set item + parents to `in_progress` before coding | Prevents orphaned work, enables tracking |
| Identify which acceptance criteria task addresses | Ensures work contributes to feature/epic goals |
| Update acceptance criteria on task close | Tracks progress, enables feature/epic closure |
| Tests must pass before closing | Broken code should never be marked complete |
| Completion notes must list files changed | Enables code review and context recovery |
| `bd sync --from-main` before session end | Prevents merge conflicts in beads |

### What Breaks If You Skip

- **Skip status updates** = Work invisible to team, parent items never close
- **Skip acceptance criteria identification** = Work may not contribute to feature goals
- **Skip acceptance criteria updates** = Features appear incomplete, can't close parents
- **Skip tests** = Bugs ship, technical debt compounds
- **Skip completion notes** = Context lost, can't review what changed
- **Skip beads sync** = Merge conflicts, lost issue updates

---

## Pre-Flight Checklist (MANDATORY GATE)

> **STOP. You may NOT write any code until ALL items below are confirmed.**
> This checklist exists because prioritizing speed over process creates invisible, untrackable work.

Before writing ANY implementation code, you MUST complete and explicitly acknowledge each item:

### 1. Plan Confirmation
- [ ] Plan has been reviewed via `/plannotator-review` OR user has explicitly approved
- [ ] You have NOT received the plan and started implementing in the same message

### 2. Beads Structure
- [ ] Run `bd sync --from-main` to get latest state
- [ ] Feature has acceptance criteria defined (`bd show <feature-id>`)
- [ ] Parent epic has acceptance criteria defined (`bd show <epic-id>`)
- [ ] Feature references its research findings (if research task exists) - add `## Research` section with path to research doc
- [ ] Implementation tasks exist in beads for each planned step (`bd list --parent <feature-id>`)
- [ ] If tasks don't exist, CREATE THEM FIRST before any code

### 3. Acceptance Criteria Mapping
- [ ] Identify which feature acceptance criteria this task addresses
- [ ] Identify which epic acceptance criteria this task contributes to
- [ ] If task doesn't map to any criteria, verify it's actually needed

### 4. Status Updates
- [ ] Feature set to `in_progress`
- [ ] Parent epic set to `in_progress`
- [ ] Current task set to `in_progress`

### 5. Explicit Acknowledgment
Before proceeding, state to the user:
```
Pre-flight checklist complete:
- Plan confirmed: [yes/no - how]
- Acceptance criteria: [feature and epic both have them]
- Research referenced: [yes/no/N/A - path to research doc if exists]
- Beads tasks: [list task IDs that will be worked]
- Status: [feature], [epic], [task] all in_progress
- This task addresses:
  - Feature criteria: [list specific criteria from feature]
  - Epic criteria: [list specific criteria from epic, or "contributes via feature"]

Ready to begin implementation.
```

**If ANY item is not complete, STOP and fix it before writing code.**

---

## Quick Reference

See: [code/workflow-implementation/workflows.md](code/workflow-implementation/workflows.md)

---

## Common Workflow

### Phase 1: Pre-Work Validation

Before starting implementation, verify ALL of the following:

**Item Validation:**
- [ ] Item exists and is not blocked (`bd show <id>`)
- [ ] Item has required fields (title, type, priority)
- [ ] GitHub Issue link is noted (if linked)

**Status Updates:**
- [ ] Set Beads item to `in_progress`
- [ ] Ensure parent Feature is `in_progress` (if task/bug under feature)
- [ ] Ensure parent Epic is `in_progress` (if feature under epic)

### Phase 2: Plan Adherence Check (Before Coding)

**Purpose:** Ensure alignment with the plan before writing code.

1. Review the Feature Plan tasks (`bd list --parent <feature-id>`)
2. Review the current task description and notes
3. Understand expected files to create/modify
4. Identify similar patterns in the codebase
5. Confirm dependencies are met

Before starting, state:
- What you're about to implement
- What files you expect to create/modify
- What approach you'll follow

### Phase 3: Implementation

**Use TodoWrite for Subtasks:**

```
Working on: "Add user validation"

Todos:
[ ] Add validation schema
[ ] Update UserService
[ ] Add unit tests
[ ] Run tests
[ ] Fix linting errors
```

Update todos as you progress. Mark complete immediately after finishing each step.

**Code Quality Guardrails:**

| Category | Requirements |
|----------|-------------|
| Tests | Required for new functionality, must test business logic, must pass |
| Code Quality | Fix linting errors, follow existing patterns, no OWASP top 10 vulnerabilities |
| Commits | After each logical unit, specific messages, no broken code |

**Commit Frequency:**
- After implementing a cohesive piece of functionality
- After adding tests for that functionality
- After fixing a distinct issue

**Do NOT:**
- Wait until end of task to commit everything
- Commit broken/untested code
- Commit with generic messages like "WIP" or "updates"

### Phase 4: Plan Adherence Check (After Coding)

**Purpose:** Verify implementation matches the plan before closing.

**Compare Plan vs. Actual:**

| Planned | Actual | Status |
|---------|--------|--------|
| Create src/schemas/user.ts | Created src/schemas/user.ts | Match |
| Update UserService | Updated UserService + UserController | Deviation |

**Document Deviations:**
```
Deviation: Also updated UserController
Reason: Controller needed validation error handling
Type: Discovered during implementation
```

**Verify Before Closing:**
- [ ] New code has tests
- [ ] Tests test actual business logic
- [ ] Tests pass
- [ ] No regressions in existing tests
- [ ] No linting errors
- [ ] Code follows project conventions

**Check Acceptance Criteria Chain:**
- [ ] Task completion contributes to Feature acceptance criteria
- [ ] Feature acceptance criteria include verification method
- [ ] Epic acceptance criteria are being addressed

### Phase 5: Closing

**Update Acceptance Criteria (MANDATORY):**

Before closing the task, update parent items:

1. **Feature acceptance criteria** - Check off `[x]` any criteria this task completes
   ```bash
   bd show <feature-id>  # Review current criteria
   bd update <feature-id> --description "..." # Update with [x] for completed items
   ```

2. **Epic acceptance criteria** - Check off `[x]` any criteria now complete
   ```bash
   bd show <epic-id>  # Review current criteria
   bd update <epic-id> --description "..." # Update with [x] for completed items
   ```

3. **Note in task closing reason** - List which acceptance criteria were addressed

**Required Completion Notes:**

| Section | Contents |
|---------|----------|
| Summary | What was implemented, deviations from plan and why |
| Files | Created, updated, removed |
| Tests | Created, updated, removed |
| Acceptance Criteria | Which feature/epic criteria this task addressed |
| Discovered Work | Bugs found/fixed with Beads IDs, new items created |

### Phase 6: Session End

1. **Apply Self-Learning Skills** - Record patterns, gotchas, techniques
2. **Sync Beads** - `bd sync --from-main`
3. **Final Commit** - Ensure all work is committed
4. **Verify Clean State**

---

## Discovered Work Handling

When you discover work that wasn't planned:

| Situation | Action |
|-----------|--------|
| Small fix in scope | Do it, document in completion notes |
| Bug found | Create Beads bug item, link as dependency if blocking |
| New feature need | Create Beads task/feature, don't scope creep |
| Technical debt | Create Beads task with priority 3-4 |

---

## Workflow Diagram

```
User asks to work on something
    |
    v
Identify Beads item
    |
    v
PRE-FLIGHT CHECKLIST (MANDATORY GATE)
+-- Plan confirmed via plannotator or explicit approval?
+-- bd sync --from-main (get latest beads state)
+-- Feature has acceptance criteria?
+-- Epic has acceptance criteria?
+-- Feature references research findings (if research exists)?
+-- Implementation tasks exist in beads?
+-- Identify which acceptance criteria this task addresses
+-- If NO to any: STOP and fix before proceeding
    |
    v
State explicit acknowledgment to user
    |
    v
Pre-Work Validation
+-- Check item not blocked
+-- Note GitHub Issue link (if any)
+-- Set item to in_progress
+-- Set parent feature to in_progress
+-- Set parent epic to in_progress
    |
    v
Plan Adherence Check (BEFORE)
+-- Review Feature Plan tasks
+-- Understand expected changes
+-- Confirm approach
+-- Document understanding
    |
    v
Implementation
+-- Use TodoWrite for subtasks
+-- Write code following plan
+-- Ensure test coverage
+-- Tests test business logic
+-- Tests pass
+-- Fix linting errors
+-- Commit after each logical unit
+-- Track discovered work in Beads
    |
    v
Plan Adherence Check (AFTER)
+-- Compare plan vs actual
+-- Document deviations
+-- Verify test coverage
+-- Verify linting clean
+-- Check acceptance criteria chain
    |
    v
Mark final todo complete
    |
    v
TodoWrite Hook Fires (all todos complete)
+-- Adherence checklist displayed
+-- Verify all items
+-- Fix any issues before proceeding
    |
    v
Closing
+-- Update feature acceptance criteria (check off completed)
+-- Update epic acceptance criteria (check off completed)
+-- Write detailed completion notes (include criteria addressed)
+-- Close Beads item
+-- Close GitHub Issue via PR (use `Fixes #N` in PR body)
    |
    v
Session End
+-- Apply self-learning skills
+-- bd sync --from-main
+-- git commit
```

---

## Common Mistakes to Avoid

1. **Skipping the pre-flight checklist** - Jumping into code without confirming plan, acceptance criteria, and beads tasks
2. **Implementing a plan in the same message it was received** - Always pause for confirmation
3. Starting work without setting parent items to `in_progress`
4. Skipping the plan review before implementation
5. **Not linking research to feature** - If a research task exists, feature description must reference its findings (e.g., `## Research\nSee: docs/research/...`)
6. **Not identifying which acceptance criteria task addresses** - Must know upfront what the task contributes to
7. **Not updating acceptance criteria on task close** - Feature/epic criteria must be checked off when tasks complete them
8. Writing code without tests
9. Tests that don't test business logic
10. Waiting until end to commit everything
11. Scope creep - doing unplanned work without tracking it
12. Closing without detailed completion notes
13. Forgetting to close GitHub Issue (use `Fixes #N` in PR)
14. Skipping self-learning skills at session end
15. Not syncing beads before ending session
