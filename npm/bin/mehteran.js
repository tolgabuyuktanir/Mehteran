#!/usr/bin/env node
// Starts Mehteran from npm: "npx mehteran [command ...]" (default: ui).
// Mehteran is a Python application that keeps the book translation's files (books/, config.toml, prompts/,
// glossary/, .runtime/) inside its code folder, so the code lives in a fixed folder that npm never deletes:
// ~/Mehteran, or MEHTERAN_DIR. The first run extracts the source bundled with this npm release.
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

const dir = path.resolve(process.env.MEHTERAN_DIR || path.join(os.homedir(), "Mehteran"));
const win = process.platform === "win32";

function fail(en, tr) {
  console.error(en + "\n" + tr);
  process.exit(1);
}

function isCopy(d) {
  return fs.existsSync(path.join(d, "scripts", "mehter.sh")) && fs.existsSync(path.join(d, "mehteran", "__main__.py"));
}

function isEmpty(d) {
  return !fs.existsSync(d) || fs.readdirSync(d).length === 0;
}

function install() {
  console.log(`Installing Mehteran into ${dir} ...\nMehteran ${dir} klasörüne kuruluyor ...`);
  fs.mkdirSync(path.dirname(dir), { recursive: true });
  const partial = fs.mkdtempSync(dir + ".partial-");
  const archive = path.join(__dirname, "..", "mehteran.tar.gz");
  try {
    const r = spawnSync("tar", ["-xzf", archive, "-C", partial], { stdio: "inherit" });
    if (r.status !== 0) throw new Error("Unpacking failed (tar).\nArşiv açılamadı (tar).");
    if (fs.existsSync(dir)) fs.rmdirSync(dir);
    fs.renameSync(partial, dir);
  } finally {
    fs.rmSync(partial, { recursive: true, force: true });
  }
}

function start(args) {
  const child = win
    ? spawn(process.env.ComSpec || "cmd.exe",
        ["/d", "/s", "/c", '"' + [path.join(dir, "mehter.cmd"), ...args].map((a) => `"${a}"`).join(" ") + '"'],
        { stdio: "inherit", windowsVerbatimArguments: true })
    : spawn("sh", [path.join(dir, "mehter"), ...args], { stdio: "inherit" });
  process.on("SIGINT", () => {}); // Ctrl+C reaches Mehteran itself, which stops cleanly
  child.on("error", (e) => fail(`Could not start Mehteran: ${e.message}`, `Mehteran başlatılamadı: ${e.message}`));
  child.on("exit", (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
}

async function main() {
  if (!isCopy(dir)) {
    if (!isEmpty(dir)) {
      fail(`${dir} exists and is not a Mehteran folder. Choose another folder with MEHTERAN_DIR.`,
        `${dir} var ve bir Mehteran klasörü değil. MEHTERAN_DIR ile başka bir klasör seçin.`);
    }
    install();
  }
  const args = process.argv.slice(2);
  start(args.length ? args : ["ui"]);
}

main().catch((e) => { console.error(e.message); process.exit(1); });
