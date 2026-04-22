#!/usr/bin/env node

const { spawn, execSync } = require("child_process");
const path = require("path");

function findPython() {
  const candidates = ["python3", "python"];
  for (const cmd of candidates) {
    try {
      const result = execSync(`${cmd} --version 2>&1`, { encoding: "utf-8" });
      const match = result.match(/Python (\d+)\.(\d+)/);
      if (match && parseInt(match[1]) >= 3 && parseInt(match[2]) >= 10) {
        return cmd;
      }
    } catch {}
  }
  return null;
}

const args = process.argv.slice(2);

if (args[0] === "--help" || args[0] === "-h") {
  console.log("cheongyak-rag-mcp — 한국 주택청약 RAG MCP 서버");
  console.log();
  console.log("Usage:");
  console.log("  npx cheongyak-rag-mcp          MCP 서버 실행");
  console.log("  npx cheongyak-rag-mcp config   설정 변경");
  console.log("  npx cheongyak-rag-mcp --help   도움말");
  console.log();
  console.log("Environment:");
  console.log("  DATA_GO_KR_API_KEY   공공데이터포털 API 키 (선택)");
  console.log("  OPENAI_API_KEY       OpenAI API 키 (선택)");
  process.exit(0);
}

const python = findPython();
if (!python) {
  console.error("Error: Python 3.10+ is required.");
  console.error("Install: https://www.python.org/downloads/");
  process.exit(1);
}

const mcpArg = args[0] === "config" ? "config" : "";
const child = spawn(
  python,
  ["-m", "rag_mcp.server", mcpArg].filter(Boolean),
  { stdio: "inherit", env: process.env }
);

child.on("exit", (code) => process.exit(code || 0));
child.on("error", (err) => {
  console.error("Failed to start:", err.message);
  process.exit(1);
});
