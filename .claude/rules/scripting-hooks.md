# Hook Scripting Standards

## Critical Rules

**CRITICAL**: All Claude Code hooks MUST be implemented as Bun scripts (TypeScript).

| DO | DO NOT |
|----|--------|
| Use Bun + TypeScript | Use Python |
| Place in `.claude/hooks/` | Use Bash/Shell scripts |
| Exit with code 0 (always) | Use Node.js |
| Fail silently | Use any other language |

**Why Bun?** Cross-platform compatibility across Windows, macOS, and Linux without additional runtime configuration.

---

## Quick Start

### 1. Create the Hook Script

File: `.claude/hooks/my-hook.ts`

```typescript
#!/usr/bin/env bun

interface HookInput {
  session_id: string;
  transcript_path: string;
  cwd: string;
  permission_mode: string;
  hook_event_name: string;
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  tool_use_id?: string;
}

async function main() {
  try {
    const input = await Bun.stdin.text();
    if (!input.trim()) process.exit(0);

    const data: HookInput = JSON.parse(input);

    // Your hook logic here

    process.exit(0);
  } catch (error) {
    process.exit(0); // Always exit cleanly
  }
}

main();
```

### 2. Register in hooks.json

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "ToolName",
        "hooks": [
          {
            "type": "command",
            "command": "bun run ${CLAUDE_PROJECT_ROOT}/.claude/hooks/my-hook.ts",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

---

## Naming Conventions

- **Location**: `.claude/hooks/`
- **Format**: kebab-case with `.ts` extension
- **Style**: Descriptive names indicating purpose

Examples:
- `check-todos-complete.ts`
- `validate-commit-message.ts`
- `enforce-test-coverage.ts`

---

## Hook Events

Common hook event types for the `matcher` field:
- `PreToolUse` - Before a tool executes
- `PostToolUse` - After a tool executes
- `PermissionRequest` - When permission is requested
- `Stop` - When session ends

---

## Testing Hooks

<commands>
```bash
# Test with sample input
echo '{"tool_name":"TodoWrite","tool_input":{"todos":[]}}' | bun run .claude/hooks/my-hook.ts
```
</commands>

---

## Error Handling

Hooks must **never break the workflow**. Always exit with code 0, even on errors.

```typescript
catch (error) {
  // Optionally log for debugging
  // await Bun.write("/tmp/hook-error.log", String(error));

  // Always exit cleanly
  process.exit(0);
}
```

**Rules:**
- **Fail silently** - Never break the workflow due to hook errors
- **Exit with 0** - Always exit successfully, even on errors
- **Log errors** - Optionally log to a file for debugging (not stdout)
