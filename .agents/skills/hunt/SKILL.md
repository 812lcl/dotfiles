---
name: hunt
description: Invoke when debugging any error, crash, unexpected behavior, or failing test. Finds root cause before applying any fix. Not for code review or new features.
version: 3.2.0
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - WebSearch
  - AskUserQuestion
---

# Hunt: Diagnose Before You Fix

A patch applied to a symptom creates a new bug somewhere else. Find the origin first.

**Do not touch code until you can state the root cause in one sentence.**

## Orientation

Start by building a complete picture of what happened:

- Get the exact error, stack trace, and steps to reproduce. If anything is missing, ask one specific question.
- Review recent changes to the files named in the error or stack trace. Regressions almost always live in recent commits.
- Trace the execution path from the symptom backward: follow the data, not intuition.
- Reproduce it yourself. If you cannot reproduce it reliably, you do not understand it yet.

Before going further, commit to a testable claim:
> "I believe the root cause is [X] because [evidence]."

The claim must name a specific file, function, line, or condition. "A state management issue" is not testable. "Stale cache in `useUser` at `src/hooks/user.ts:42` because the dependency array is missing `userId`" is testable. If you cannot be that specific, you do not have a hypothesis yet.

## Known Failure Shapes

When a hypothesis is hard to form, match the symptom to a known shape:

| Shape | Clues | Where to look |
|-------|-------|---------------|
| Timing problem | Intermittent, load-dependent | Concurrent access to shared state |
| Missing guard | Crash on field or index access | Optional values, empty collections |
| Ordering bug | Works in isolation, fails in sequence | Event callbacks, transaction scope |
| Boundary failure | Timeout, wrong response shape | External APIs, service edges |
| Environment mismatch | Local pass, CI fail | Env vars, feature flags, seeded data |
| Stale value | Old data shown, refreshes on restart | In-memory cache, memoized result |
| Condition wait | Sleeping for time instead of state | Replace fixed sleeps with polling: check file exists, port responds, or process exits |

Also worth checking: existing TODOs near the failure site, and whether this area has been patched before. Recurring fixes in the same place mean the abstraction is wrong.

Pay attention to deflection. When a developer or user says "that part doesn't matter" or "don't worry about that area," treat it as a signal rather than a clearance. The area someone is reluctant to examine is often where the actual problem lives.

## Check the Knowledge Store

Before deep investigation, search for prior solutions to the same or similar bug in `docs/solutions/` (if it exists). If a match is found, read the solution file. It may contain the root cause, what approaches failed, and the fix. This can save an entire investigation.

## Check for Known Issues

Before deep investigation, search open issues and recent CI failures for the same symptom. If `gh` is not installed, install it first.

## Confirm or Discard the Hypothesis

Add one targeted instrument: a log line, a failing assertion, or the smallest possible test that would fail if the hypothesis is correct. Run it.

If the evidence contradicts the hypothesis, discard it completely and re-orient with what was just learned. Do not preserve a hypothesis that the evidence disproves.

After three failed hypotheses, stop. Do not guess a fourth time. Instead, surface the situation to the user: what was checked, what was ruled out, what is still unknown. Ask whether to add more instrumentation, escalate, or approach the problem differently.

**Same symptom after a fix is a hard stop.** If the user reports the same symptom after a patch was applied, do not patch again. Treat it as a new investigation: the previous hypothesis was wrong. Re-read the execution path from scratch. Three rounds of "fixed but still broken" in the same area means the abstraction is wrong, not the specific line.

**Never state environment details from memory.** Before diagnosing OS, compiler, SDK, or tool version issues, run the detection command first: `sw_vers`, `xcodebuild -version`, `node --version`, `rustc --version`, etc. State the actual output. A diagnosis built on an assumed version is not a diagnosis.

**External tool or MCP failure: diagnose before switching.** When an MCP tool, CLI dependency, or external API is unavailable or returning errors, do not immediately try an alternative method. First determine why it failed: is the server running? Is the API key valid or expired? Is the config pointing to the right endpoint? Is a proxy needed? Switching to a workaround without diagnosing the root cause leaves the original problem intact and wastes the next session too.

Stop and reassess if you catch yourself:
- Writing a fix before you have finished tracing the flow
- Thinking "let me just try this"
- Finding that each fix surfaces a new problem in a different module

## Rationalization Watch

These phrases are diagnostic failures in disguise. When one surfaces, stop and re-examine:

| What you're thinking | What it actually means | Rule |
|---|---|---|
| "I'll just try this one thing" | No hypothesis, random-walking | Stop. Write the hypothesis first. |
| "I'm confident it's X" | Confidence is not evidence | Run an instrument that proves it. |
| "Probably the same issue as before" | Treating a new symptom as a known pattern | Re-read the execution path from scratch. |
| "It works on my machine" | Environment difference IS the bug | Enumerate every env difference before dismissing it. |
| "One more restart should fix it" | Avoiding the error message | Read the last error verbatim. Never restart more than twice without new evidence. |

## Apply the Fix

Once the root cause is confirmed:

- Fix the cause, not the symptom it produces
- Keep the diff small: fewest files, fewest lines
- Write one regression test that fails on the unfixed code and passes after the fix. If the bug is non-testable (timing, environment-specific, UI rendering), document why and add the best available guard instead.
- For large projects, run the targeted subset first (tests in the affected module). Run the full suite only after the targeted tests pass. Paste the full output, no summaries.
- If the change touches more than 5 files, pause and confirm the scope with the user

**Self-regulation:** track how the fix is going. If you have reverted the same area twice, or if the current fix touches more than 3 files for what started as a single bug, stop. Do not keep patching. Describe what is known and unknown, and ask the user how to proceed. Continued patching past this point means the abstraction is wrong, not the code.

After the fix lands, consider whether a second layer of defense makes sense: validate the same condition at the call site, the service boundary, or in a test. A bug that cannot be introduced again is better than a bug that was fixed once.

## Gotchas

Real failures from prior sessions, in order of frequency:

- **Fixed the wrong code path.** Patched the client pane instead of the local pane because I guessed the location from the symptom. Trace the execution path from the symptom backward before touching any file.
- **Same symptom, four patches.** Applied a fix, got the same error back, patched again. Each patch buried the real cause deeper. Same symptom after a fix = stop and re-read the whole execution path from scratch.
- **Stated macOS version from memory.** Diagnosed a notarytool failure as "macOS 26 beta." It was a stable release. Run `sw_vers` first. A diagnosis built on assumed versions is not a diagnosis.
- **Tried workarounds before diagnosing tool failure.** xcrawl MCP wasn't loading; I tried WebFetch instead of checking why. Check server status, API key validity, and config before switching methods.
- **Wrote the fix before finishing the trace.** "Let me just try this" is a red flag. It means the hypothesis is incomplete. Stop, finish the trace, write the hypothesis in one sentence, then write the fix.
- **Blind restart loop.** Restarted the server 8 times, changing one variable each time without reading the actual error response body. Read the last error verbatim before restarting; never restart more than twice without a new evidence-based hypothesis.
- **Pipeline healthy but no output.** Orchestrator reported RUNNING, but TTS vendor was misconfigured. Polled status instead of testing each stage. In multi-stage pipelines (ASR->LLM->TTS), test each stage in isolation when the orchestrator says healthy but output is missing.

## Outcome

End with a short summary:

```
Root cause:  [what was wrong, file:line]
Fix:         [what changed, file:line]
Confirmed:   [evidence or test that proves the fix]
Tests:       [pass/fail count, regression test location]
```

Status is one of: **resolved**, **resolved with caveats** (state them), or **blocked** (state what is unknown and why).
