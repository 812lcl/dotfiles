// OpenCode V2 plugin. Read the session location, never the server process cwd.
import { execFile } from "node:child_process";
import { homedir } from "node:os";
import { join } from "node:path";

const python = "/opt/homebrew/opt/python@3.14/bin/python3.14";
const adapter = join(homedir(), "Code/dotfiles/agent-runtime/brain_hooks.py");

export async function invoke(event, directory) {
  try {
    const stdout = await new Promise((resolve, reject) => {
      const child = execFile(python, ["-B", adapter, "opencode", event], {
        timeout: 25000, maxBuffer: 128 * 1024,
      }, (error, stdout) => error ? reject(error) : resolve(stdout));
      child.stdin.on("error", () => {});
      child.stdin.end(JSON.stringify({ cwd: directory }));
    });
    return JSON.parse(stdout);
  } catch { return {}; }
}

export default {
  id: "agent-runtime.brain",
  async setup(ctx) {
    if (!ctx?.session?.hook) return;
    async function run(event, sessionID) {
      try {
        const session = await ctx.session.get({ sessionID });
        if (session.parentID || !session.location?.directory) return {};
        return await invoke(event, session.location.directory);
      } catch { return {}; }
    }
    await ctx.session.hook("context", async (event) => {
      const result = await run("context", event.sessionID);
      if (result.context) event.system.push({ type: "text", text: result.context });
    });
    await ctx.session.hook("experimental.idle", async (event) => {
      await run("stop", event.sessionID);
    });
  },
};
