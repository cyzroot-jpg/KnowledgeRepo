#!/usr/bin/env node
// Generate a directory tree of folders and markdown files, then inject it
// into README.md between the TREE:START / TREE:END markers.
//
// Usage: node scripts/gen-tree.mjs

import { readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const README = join(ROOT, "README.md");

const START = "<!-- TREE:START -->";
const END = "<!-- TREE:END -->";

const IGNORED_DIRS = new Set([
  ".git",
  ".github",
  ".idea",
  ".vscode",
  "__pycache__",
  "node_modules",
  "scripts",
  "image",
  "images",
]);

const ROOT_LABEL = "KnowledgeRepo/";

/** True if the directory (or any subdirectory) contains a .md file. */
function hasMarkdown(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith(".") || IGNORED_DIRS.has(entry.name)) continue;
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (hasMarkdown(full)) return true;
    } else if (entry.isFile() && entry.name.toLowerCase().endsWith(".md")) {
      return true;
    }
  }
  return false;
}

/** Return [subdirs, markdownFiles] for a directory, filtered and sorted. */
function collect(dir) {
  const subdirs = [];
  const files = [];

  const entries = readdirSync(dir, { withFileTypes: true }).sort((a, b) =>
    a.name.toLowerCase().localeCompare(b.name.toLowerCase()),
  );

  for (const entry of entries) {
    if (entry.name.startsWith(".") || IGNORED_DIRS.has(entry.name)) continue;
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (hasMarkdown(full)) subdirs.push(full);
    } else if (entry.isFile() && entry.name.toLowerCase().endsWith(".md")) {
      files.push(full);
    }
  }

  return [subdirs, files];
}

function buildTree(dir, prefix = "") {
  const [subdirs, files] = collect(dir);
  const entries = [
    ...subdirs.map((p) => ({ path: p, isDir: true })),
    ...files.map((p) => ({ path: p, isDir: false })),
  ];

  const lines = [];
  entries.forEach(({ path, isDir }, index) => {
    const last = index === entries.length - 1;
    const connector = last ? "└── " : "├── ";
    const name = path.slice(dir.length + 1) + (isDir ? "/" : "");
    lines.push(`${prefix}${connector}${name}`);
    if (isDir) {
      lines.push(...buildTree(path, prefix + (last ? "    " : "│   ")));
    }
  });

  return lines;
}

function renderTree() {
  return [ROOT_LABEL, ...buildTree(ROOT)].join("\n");
}

function updateReadme(tree) {
  const content = readFileSync(README, "utf8");

  if (!content.includes(START) || !content.includes(END)) {
    console.error(`Markers ${START} / ${END} not found in README.md.`);
    process.exit(1);
  }

  const head = content.slice(0, content.indexOf(START));
  const tail = content.slice(content.indexOf(END) + END.length);
  const next = `${head}${START}\n\`\`\`\n${tree}\n\`\`\`\n${END}${tail}`;

  if (next === content) return false;
  writeFileSync(README, next, "utf8");
  return true;
}

const changed = updateReadme(renderTree());
console.log(changed ? "README.md updated." : "README.md already up to date.");