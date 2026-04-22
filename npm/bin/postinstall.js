#!/usr/bin/env node

const { execSync } = require("child_process");

const commands = [
  "pip3 install cheongyak-rag-mcp --break-system-packages --quiet",
  "pip install cheongyak-rag-mcp --break-system-packages --quiet",
  "pip3 install cheongyak-rag-mcp --quiet",
  "pip install cheongyak-rag-mcp --quiet",
];

let installed = false;
for (const cmd of commands) {
  try {
    execSync(cmd, { stdio: "pipe" });
    installed = true;
    break;
  } catch {}
}

if (!installed) {
  console.warn(
    "[cheongyak-rag-mcp] pip install failed. Install manually:\n" +
    "  pip install cheongyak-rag-mcp"
  );
}
