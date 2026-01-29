# Scripting Safety Standards

## Critical Rules

**Before modifying files in a git repository, verify they are clean (committed).**

Scripts that modify existing files should:
1. Check target files have no uncommitted changes
2. Exit early with clear error if dirty files found
3. List the dirty files so user knows what to commit/stash

---

## Pre-Flight Check Pattern

```bash
# Check if specific files have uncommitted changes
git status --porcelain <path>

# Empty output = clean, any output = dirty
```

### PowerShell Implementation

```powershell
function Test-FilesClean {
    param([string]$RepoPath, [array]$Paths)

    Push-Location $RepoPath
    try {
        $dirtyFiles = @()
        foreach ($path in $Paths) {
            $status = git status --porcelain $path 2>$null
            if ($status) { $dirtyFiles += $path }
        }

        if ($dirtyFiles.Count -gt 0) {
            Write-Host "Error: Uncommitted changes:" -ForegroundColor Red
            $dirtyFiles | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
            return $false
        }
        return $true
    }
    finally { Pop-Location }
}

# Usage: Exit if files are dirty
if (-not (Test-FilesClean -RepoPath $Target -Paths @("file1", "file2"))) {
    exit 1
}
```

### Bash Implementation

```bash
check_files_clean() {
    local repo_path="$1"
    shift
    local paths=("$@")
    local dirty_files=()

    pushd "$repo_path" > /dev/null
    for path in "${paths[@]}"; do
        local status=$(git status --porcelain "$path" 2>/dev/null || true)
        [[ -n "$status" ]] && dirty_files+=("$path")
    done
    popd > /dev/null

    if [[ ${#dirty_files[@]} -gt 0 ]]; then
        echo "Error: Uncommitted changes:"
        printf '  %s\n' "${dirty_files[@]}"
        return 1
    fi
    return 0
}

# Usage: Exit if files are dirty
check_files_clean "$TARGET" "file1" "file2" || exit 1
```

---

## When to Use

| Script Type | Pre-flight Check? |
|-------------|-------------------|
| Setup/migration scripts | **Yes** - modifies existing files |
| Build scripts | No - generates artifacts |
| Test scripts | No - read-only |
| Deployment scripts | **Yes** - may modify config |

---

## Error Messages

Provide actionable error messages:

```
Error: The following files have uncommitted changes:
  .claude/settings.json
  CLAUDE.md

Please commit or stash your changes before running this script.
```

**Include:**
- List of dirty files
- Clear action for user (commit or stash)
- No cryptic exit codes without explanation
