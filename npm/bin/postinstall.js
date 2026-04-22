#!/usr/bin/env node

const { execSync } = require("child_process");

const VERSION = "0.2.0";

const commands = [
  `pip3 install cheongyak-rag-mcp==${VERSION} --break-system-packages`,
  `pip install cheongyak-rag-mcp==${VERSION} --break-system-packages`,
  `pip3 install cheongyak-rag-mcp==${VERSION}`,
  `pip install cheongyak-rag-mcp==${VERSION}`,
];

let installed = false;
for (const cmd of commands) {
  try {
    execSync(cmd, { stdio: "pipe" });
    installed = true;
    console.log(`[cheongyak-rag-mcp] v${VERSION} installed successfully.`);
    break;
  } catch {}
}

if (!installed) {
  console.warn(
    `[cheongyak-rag-mcp] pip install failed. Install manually:\n` +
    `  pip install cheongyak-rag-mcp==${VERSION}`
  );
}
