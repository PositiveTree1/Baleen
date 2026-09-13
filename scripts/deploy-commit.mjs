import { spawnSync } from "node:child_process";

const args = process.argv.slice(2);
const shouldPush = args.includes("--push");
const commitMessage = args.filter((arg) => arg !== "--push").join(" ").trim();

function run(command, commandArgs, options = {}) {
  const result = spawnSync(command, commandArgs, {
    encoding: "utf8",
    stdio: options.capture ? "pipe" : "inherit",
    shell: process.platform === "win32",
  });

  if (result.status !== 0) {
    if (options.capture && result.stderr) {
      process.stderr.write(result.stderr);
    }
    process.exit(result.status ?? 1);
  }

  return (result.stdout ?? "").trim();
}

function printUsageAndExit() {
  console.error('Usage: npm run deploy -- "Commit message"');
  console.error('       npm run deploy:commit -- "Commit message"');
  process.exit(1);
}

if (!commitMessage) {
  printUsageAndExit();
}

run("git", ["rev-parse", "--is-inside-work-tree"], { capture: true });

const currentBranch = run("git", ["branch", "--show-current"], { capture: true });
if (!currentBranch) {
  console.error("Refusing to deploy from a detached HEAD. Check out a branch first.");
  process.exit(1);
}

run("git", ["add", "--all"]);

const hasTrackedChanges = spawnSync("git", ["diff", "--cached", "--quiet"], {
  shell: process.platform === "win32",
}).status !== 0;
const untrackedFiles = run("git", ["ls-files", "--others", "--exclude-standard"], {
  capture: true,
});

if (!hasTrackedChanges && !untrackedFiles) {
  console.log("No local changes to commit.");
  if (shouldPush) {
    run("git", ["push", "origin", "HEAD"]);
  }
  process.exit(0);
}

run("git", ["commit", "-m", commitMessage]);

if (shouldPush) {
  run("git", ["push", "origin", "HEAD"]);
  console.log(`Pushed ${currentBranch} to origin. Railway and Vercel should pick up the new commit.`);
} else {
  console.log("Created commit locally. Run npm run deploy:push to trigger Railway and Vercel.");
}
