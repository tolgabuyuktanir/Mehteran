#!/usr/bin/env node
// Starts Mehteran from npm: "npx mehteran [command ...]" (default: ui).
// Mehteran is a Python application that keeps the book translation's files (books/, config.toml, prompts/,
// glossary/, .runtime/) inside its code folder, so the code lives in a fixed folder that npm never deletes:
// ~/Mehteran, or MEHTERAN_DIR. The first run installs it there (git clone; without git, the GitHub archive),
// later runs start it. The launcher in that folder finds Python and brings a git copy up to date.
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

const REPO = "https://github.com/tolgabuyuktanir/Mehteran";
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

function hasGit() {
  return spawnSync("git", ["--version"], { stdio: "ignore" }).status === 0;
}

async function install() {
  console.log(`Installing Mehteran into ${dir} ...\nMehteran ${dir} klasörüne kuruluyor ...`);
  if (hasGit()) {
    if (fs.existsSync(dir)) fs.rmdirSync(dir); // empty: git clone wants to create it
    const r = spawnSync("git", ["clone", REPO + ".git", dir], { stdio: "inherit" });
    if (r.status !== 0) fail("git clone failed.", "git clone başarısız oldu.");
    return;
  }
  const partial = dir + ".partial";
  fs.rmSync(partial, { recursive: true, force: true });
  fs.mkdirSync(partial, { recursive: true });
  const archive = path.join(os.tmpdir(), `mehteran-${process.pid}.tar.gz`);
  try {
    const res = await fetch(`${REPO}/archive/refs/heads/main.tar.gz`);
    if (!res.ok) throw new Error(`Download failed: HTTP ${res.status}.\nİndirme başarısız: HTTP ${res.status}.`);
    fs.writeFileSync(archive, Buffer.from(await res.arrayBuffer()));
    const r = spawnSync("tar", ["-xzf", archive, "--strip-components=1", "-C", partial], { stdio: "inherit" });
    if (r.status !== 0) throw new Error("Unpacking failed (tar).\nArşiv açılamadı (tar).");
  } catch (e) {
    fs.rmSync(partial, { recursive: true, force: true });
    throw e;
  } finally {
    fs.rmSync(archive, { force: true });
  }
  if (fs.existsSync(dir)) fs.rmdirSync(dir);
  fs.renameSync(partial, dir);
  console.log("Installed without git: install git for automatic updates.\n"
    + "git olmadan kuruldu: otomatik güncellemeler için git kurun.");
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
    await install();
  }
  const args = process.argv.slice(2);
  start(args.length ? args : ["ui"]);
}

main().catch((e) => { console.error(e.message); process.exit(1); });
