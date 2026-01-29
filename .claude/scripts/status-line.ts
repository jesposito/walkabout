#!/usr/bin/env bun

/**
 * Status line script for Claude Code
 * Shows: Model | Branch ±changes | Beads health | Current item | Nk↓ Nk↑ (N%)
 */

import { spawn } from "bun";

// ANSI color codes
const colors = {
  reset: "\x1b[0m",
  dim: "\x1b[2m",
  bold: "\x1b[1m",
  // Foreground
  cyan: "\x1b[36m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  magenta: "\x1b[35m",
  blue: "\x1b[34m",
  red: "\x1b[31m",
  white: "\x1b[37m",
};

interface StatusInput {
  model?: {
    display_name?: string;
  };
  context_window?: {
    total_input_tokens?: number;
    total_output_tokens?: number;
    remaining_percentage?: number;
  };
}

interface BeadsItem {
  id: string;
  title: string;
  issue_type: string; // JSONL uses issue_type, not type
  status: string;
  priority?: number;
  parent?: string;
  description?: string;
  dependencies?: Array<{ type: string; depends_on_id: string }>;
}

interface BeadsStats {
  summary: {
    total_issues: number;
    open_issues: number;
    in_progress_issues: number;
    closed_issues: number;
    blocked_issues: number;
    ready_issues: number;
  };
}

function parseGitHubIssueLink(description?: string): string | null {
  if (!description) return null;
  // Match "GitHub Issue: #123" or "GitHub Issue #123" or just "#123"
  const match = description.match(/(?:GitHub Issue[:\s]*)?#(\d+)/i);
  return match ? match[1] : null;
}

async function runCommand(cmd: string[]): Promise<string> {
  try {
    const proc = spawn(cmd, { stdout: "pipe", stderr: "ignore" });
    const text = await new Response(proc.stdout).text();
    return text.trim();
  } catch {
    return "";
  }
}

async function getGitBranch(): Promise<string> {
  const result = await runCommand(["git", "branch", "--show-current"]);
  return result || "no-git";
}

interface GitChanges {
  added: number;
  modified: number;
  deleted: number;
}

async function getGitChanges(): Promise<GitChanges> {
  const result = await runCommand(["git", "status", "--short"]);
  if (!result) return { added: 0, modified: 0, deleted: 0 };

  const lines = result.split("\n").filter((l) => l.trim());
  let added = 0;
  let modified = 0;
  let deleted = 0;

  for (const line of lines) {
    const status = line.substring(0, 2);
    // First char = staged, second char = unstaged
    // A = added, M = modified, D = deleted, ? = untracked, R = renamed
    if (status.includes("?") || status.includes("A")) {
      added++;
    } else if (status.includes("D")) {
      deleted++;
    } else if (status.includes("M") || status.includes("R")) {
      modified++;
    }
  }

  return { added, modified, deleted };
}

async function getBeadsStats(): Promise<BeadsStats | null> {
  try {
    const result = await runCommand(["bd", "stats", "--json", "--no-activity"]);
    if (!result) return null;
    return JSON.parse(result) as BeadsStats;
  } catch {
    return null;
  }
}

async function getBeadsItemsByStatus(status: string): Promise<BeadsItem[]> {
  try {
    // bd export outputs JSONL (one JSON object per line)
    const result = await runCommand(["bd", "export", "--status", status]);
    if (!result) return [];
    const lines = result.split("\n").filter((l) => l.trim());
    return lines.map((line) => JSON.parse(line) as BeadsItem);
  } catch {
    return [];
  }
}

function getParentId(item: BeadsItem): string | null {
  if (!item.dependencies) return null;
  const parentDep = item.dependencies.find((d) => d.type === "parent-child");
  return parentDep ? parentDep.depends_on_id : null;
}

async function getBeadsHealth() {
  // Get stats from bd stats --json (fast, has all counts)
  const stats = await getBeadsStats();

  // Get in-progress items for current item and progress display
  const inProgressItems = await getBeadsItemsByStatus("in_progress");

  // Extract counts from stats, default to 0 if unavailable
  const active = stats?.summary?.in_progress_issues ?? 0;
  const ready = stats?.summary?.ready_issues ?? 0;
  const blocked = stats?.summary?.blocked_issues ?? 0;

  // For bugs, we need to check the in-progress items
  // (bd stats doesn't break down by type, so we check what we have)
  const bugs = inProgressItems.filter((i) => i.issue_type === "bug").length;

  // Epic/Feature progress - find active ones
  const activeEpic = inProgressItems.find((i) => i.issue_type === "epic");
  const activeFeature = inProgressItems.find((i) => i.issue_type === "feature");

  let epicProgress = "";
  let featureProgress = "";

  // For progress, we need to get all items to count children
  // Only fetch if we have an active epic or feature
  if (activeEpic || activeFeature) {
    // Get all non-closed items to calculate progress
    const openItems = await getBeadsItemsByStatus("open");
    const allActiveItems = [...inProgressItems, ...openItems];

    // Also need closed items for accurate progress
    const closedItems = await getBeadsItemsByStatus("closed");
    const allItems = [...allActiveItems, ...closedItems];

    if (activeEpic) {
      const epicChildren = allItems.filter(
        (i) => getParentId(i) === activeEpic.id
      );
      const epicClosed = epicChildren.filter(
        (i) => i.status === "closed"
      ).length;
      const epicTotal = epicChildren.length;
      if (epicTotal > 0) {
        epicProgress = `${epicClosed}/${epicTotal}`;
      }
    }

    if (activeFeature) {
      const featureChildren = allItems.filter(
        (i) => getParentId(i) === activeFeature.id
      );
      const featureClosed = featureChildren.filter(
        (i) => i.status === "closed"
      ).length;
      const featureTotal = featureChildren.length;
      if (featureTotal > 0) {
        featureProgress = `${featureClosed}/${featureTotal}`;
      }
    }
  }

  // Get current in-progress item (prefer task over feature over epic)
  let currentItem: BeadsItem | undefined;
  const tasks = inProgressItems.filter(
    (i) => i.issue_type === "task" || i.issue_type === "bug"
  );
  const features = inProgressItems.filter((i) => i.issue_type === "feature");
  const epics = inProgressItems.filter((i) => i.issue_type === "epic");

  if (tasks.length > 0) {
    currentItem = tasks[0];
  } else if (features.length > 0) {
    currentItem = features[0];
  } else if (epics.length > 0) {
    currentItem = epics[0];
  }

  return {
    active,
    ready,
    bugs,
    blocked,
    epicProgress,
    featureProgress,
    currentItem,
  };
}

async function main() {
  // Read JSON input from stdin with a timeout
  let input: StatusInput = {};
  try {
    const chunks: Uint8Array[] = [];
    const reader = Bun.stdin.stream().getReader();

    const readWithTimeout = async () => {
      const timeoutPromise = new Promise<null>((resolve) =>
        setTimeout(() => resolve(null), 100)
      );
      const readPromise = reader.read();
      return Promise.race([readPromise, timeoutPromise]);
    };

    let result = await readWithTimeout();
    while (result && !result.done && result.value) {
      chunks.push(result.value);
      result = await readWithTimeout();
    }

    if (chunks.length > 0) {
      const decoder = new TextDecoder();
      const text = chunks.map((c) => decoder.decode(c)).join("");
      if (text.trim()) {
        input = JSON.parse(text);
      }
    }
  } catch {
    // Ignore parse errors, use defaults
  }

  // Get all data in parallel
  const [branch, changes, beadsHealth] = await Promise.all([
    getGitBranch(),
    getGitChanges(),
    getBeadsHealth(),
  ]);

  const { active, ready, bugs, blocked, epicProgress, featureProgress, currentItem } =
    beadsHealth;

  // Build status parts with colors
  const { reset, dim, cyan, green, yellow, magenta, blue, red } = colors;

  const model = input.model?.display_name || "Claude";
  const modelColored = `🤖 ${cyan}${model}${reset}`;

  // Branch with red/green change indicators
  const { added, modified, deleted } = changes;
  const totalChanges = added + modified + deleted;
  let branchColored: string;

  if (totalChanges === 0) {
    branchColored = `🌿 ${green}${branch}${reset}`;
  } else {
    const changeParts: string[] = [];
    if (added > 0) changeParts.push(`${green}+${added}${reset}`);
    if (modified > 0) changeParts.push(`${yellow}~${modified}${reset}`);
    if (deleted > 0) changeParts.push(`${red}-${deleted}${reset}`);
    branchColored = `🌿 ${yellow}${branch}${reset} ${changeParts.join(" ")}`;
  }

  // Beads health section
  const healthParts: string[] = [];

  // Active count
  if (active > 0) {
    healthParts.push(`⚡ ${magenta}${active}${reset}`);
  } else {
    healthParts.push(`${dim}⚡ 0${reset}`);
  }

  // Ready count
  if (ready > 0) {
    healthParts.push(`📋 ${blue}${ready}${reset}`);
  } else {
    healthParts.push(`${dim}📋 0${reset}`);
  }

  // Bug count (only show if > 0)
  if (bugs > 0) {
    healthParts.push(`🐛 ${red}${bugs}${reset}`);
  }

  // Blocked count (only show if > 0)
  if (blocked > 0) {
    healthParts.push(`🚫 ${red}${blocked}${reset}`);
  }

  const healthSection = healthParts.join(" ");

  // Progress section (epic/feature)
  let progressSection = "";
  if (epicProgress || featureProgress) {
    const parts: string[] = [];
    if (epicProgress) {
      parts.push(`🏔️ ${cyan}${epicProgress}${reset}`);
    }
    if (featureProgress) {
      parts.push(`✨ ${blue}${featureProgress}${reset}`);
    }
    progressSection = parts.join(" ");
  }

  // Current item with priority coloring and GitHub Issue link
  let itemColored: string;
  if (!currentItem) {
    itemColored = `${dim}💤 Ready${reset}`;
  } else {
    const priority = currentItem.priority ?? 2;
    // P0/P1 = red (urgent), P2 = yellow (normal), P3/P4 = green (low)
    const priorityColor = priority <= 1 ? red : priority === 2 ? yellow : green;
    const priorityEmoji = priority <= 1 ? "🔥" : priority === 2 ? "🎯" : "🌱";
    const shortTitle =
      currentItem.title.length > 30
        ? currentItem.title.substring(0, 27) + "..."
        : currentItem.title;

    // Check for GitHub Issue link
    const hasGhIssue = parseGitHubIssueLink(currentItem.description) !== null;
    const ghIndicator = hasGhIssue ? ` 🐙` : "";

    itemColored = `${priorityEmoji} ${priorityColor}${currentItem.id}${reset}${ghIndicator} ${priorityColor}${shortTitle}${reset}`;
  }

  const sep = `${dim}|${reset}`;
  let status = `${modelColored} ${sep} ${branchColored} ${sep} ${healthSection}`;

  if (progressSection) {
    status += ` ${sep} ${progressSection}`;
  }

  status += ` ${sep} ${itemColored}`;

  // Add token info if available
  const totalIn = input.context_window?.total_input_tokens || 0;
  const totalOut = input.context_window?.total_output_tokens || 0;
  const remaining = input.context_window?.remaining_percentage;

  if (remaining !== undefined && totalIn > 0) {
    const inK = Math.floor(totalIn / 1000);
    const outK = Math.floor(totalOut / 1000);
    // Color based on remaining context: green > 50%, yellow 20-50%, red < 20%
    const pctColor = remaining > 50 ? green : remaining > 20 ? yellow : red;
    const contextEmoji = remaining > 50 ? "🧠" : remaining > 20 ? "⚠️" : "🔴";
    // Input tokens: cyan, Output tokens: magenta
    status += ` ${sep} ${contextEmoji} ${cyan}${inK}k↓${reset} ${magenta}${outK}k↑${reset} ${pctColor}(${remaining.toFixed(0)}%)${reset}`;
  }

  console.log(status);
}

main().catch(() => process.exit(0));
