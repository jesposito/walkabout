#!/usr/bin/env bun

/**
 * PostToolUse hook for TodoWrite
 *
 * Checks if all todos are complete and outputs adherence checklist if so.
 *
 * Input (via stdin): JSON with tool_input.todos array
 * Output (via stdout): Adherence checklist message if all complete, empty otherwise
 */

interface Todo {
  content: string;
  status: "pending" | "in_progress" | "completed";
  activeForm: string;
}

interface HookInput {
  session_id: string;
  transcript_path: string;
  cwd: string;
  permission_mode: string;
  hook_event_name: string;
  tool_name: string;
  tool_input: {
    todos: Todo[];
  };
  tool_use_id: string;
}

async function main() {
  try {
    // Read JSON input from stdin
    const input = await Bun.stdin.text();

    if (!input.trim()) {
      process.exit(0);
    }

    const data: HookInput = JSON.parse(input);

    // Get todos from the input
    const todos = data.tool_input?.todos || [];

    // If no todos, nothing to check
    if (todos.length === 0) {
      process.exit(0);
    }

    // Check if ALL todos are completed
    const allComplete = todos.every(todo => todo.status === "completed");

    if (allComplete) {
      // Output the adherence checklist
      const message = `
╔════════════════════════════════════════════════════════════════════╗
║           IMPLEMENTATION ADHERENCE CHECK TRIGGERED                 ║
║                  All todos are complete!                           ║
╠════════════════════════════════════════════════════════════════════╣
║  Before finishing, verify ALL of the following:                    ║
║                                                                    ║
║  CODE QUALITY:                                                     ║
║  [ ] Tests exist for new code                                      ║
║  [ ] Tests test business logic (not just existence)                ║
║  [ ] All tests pass (run them now if not done)                     ║
║  [ ] No linting errors                                             ║
║                                                                    ║
║  PLAN ADHERENCE:                                                   ║
║  [ ] Plan vs actual comparison documented                          ║
║  [ ] Any deviations explained                                      ║
║  [ ] Acceptance criteria chain reviewed (task→feature→epic)        ║
║                                                                    ║
║  COMPLETION NOTES:                                                 ║
║  [ ] Files created/updated/removed listed                          ║
║  [ ] Tests created/updated/removed listed                          ║
║  [ ] Discovered work tracked in Beads                              ║
║                                                                    ║
║  CLOSING:                                                          ║
║  [ ] Beads item has detailed completion notes                      ║
║  [ ] GitHub Issue closed via PR (if linked)                        ║
║                                                                    ║
╠════════════════════════════════════════════════════════════════════╣
║  If ANY items are INCOMPLETE:                                      ║
║  → DO NOT STOP. Continue working to address them.                  ║
║                                                                    ║
║  If ALL items are VERIFIED:                                        ║
║  → Proceed with closing the Beads items.                           ║
╚════════════════════════════════════════════════════════════════════╝
`;
      console.log(message);
    }

    // Exit successfully
    process.exit(0);

  } catch (error) {
    // Silent fail - don't break the workflow
    process.exit(0);
  }
}

main();
