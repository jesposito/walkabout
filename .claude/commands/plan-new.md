---
allowed-tools:
  - Read
  - Glob
  - Grep
  - Task
  - AskUserQuestion
  - EnterPlanMode
description: Start a new planning workflow (Master Plan or Feature Plan)
---

# Planning Workflow

You are starting a planning workflow. Follow these steps exactly:

## Step 1: Ask Plan Type

Use the AskUserQuestion tool to ask the user which type of plan they are creating:

**Question**: "What type of plan are you creating?"
**Options**:
- **Master Plan** - Creates an Epic and Features for new major work
- **Feature Plan** - Creates Tasks for implementing a specific feature

## Step 2: If Feature Plan, Get Feature ID

If the user selects "Feature Plan", use AskUserQuestion to ask:

**Question**: "Which feature are you planning? Enter the Beads feature ID (e.g., devenv-001)"

Allow free text input for the feature ID.

## Step 3: Enter Planning Mode

After gathering the required information, use the EnterPlanMode tool to enter planning mode.

Then follow the appropriate workflow from `.claude/rules/workflow-planning.md`:

### For Master Plan:
1. Explore the codebase to understand existing architecture
2. Ask if user has a related GitHub Issue/milestone
3. Design the epic and features breakdown
4. Write plan to the plan file
5. Exit planning mode for approval

### For Feature Plan:
1. Review the feature details using `bd show <feature-id>`
2. Explore relevant code areas
3. Design the task breakdown
4. Write plan to the plan file
5. Exit planning mode for approval

## Important

- Always follow `.claude/rules/workflow-planning.md` for detailed steps
- Check for GitHub Issue links before creating items
- Include acceptance criteria for Master Plans
