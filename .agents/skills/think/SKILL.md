---
name: think
description: Invoke before writing any code for a new feature, design, or architecture decision. Turns rough ideas into approved plans with validated structure. Not for bug fixes or small edits.
version: 3.2.0
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - WebSearch
  - AskUserQuestion
---

# Think: Design and Validate Before You Build

Turn a rough idea into a clear, approved plan, then pressure-test the architecture before a line of code is written.

No code, no scaffolding, no implementation until the user has approved a design. No code snippets, no pseudo-code, no "just to illustrate" examples. Words and diagrams only.

Give opinions directly. Avoid: "That's an interesting approach," "There are many ways to think about this," "You might want to consider." Take a position and state what evidence would change it.

## Phase 0: Assess Depth

Before reading any files, assess the task scope from the user's description.

| Depth | Characteristics | Work Units |
|-------|----------------|------------|
| **Lightweight** | Single file, config change, simple addition. Low ambiguity. | 2-4 |
| **Standard** | Multi-file feature, integration, moderate complexity. | 3-6 |
| **Deep** | New system, cross-cutting change, unfamiliar domain, or high risk. | 4-8+ |

A "work unit" is one focused implementation step that produces a testable result.

State the depth in one line: "Depth: Lightweight / Standard / Deep -- reason."

**Auto-reclassification:** if Phase 1 or Phase 2 reveals an external contract surface (third-party API, undocumented system behavior, shared type exported to callers), bump up one depth level and note why.

## Phase 1: Understand the Problem

Review recent commit history and read CLAUDE.md (if present). Then read the files the user mentioned or that are obviously related to the idea (entry points, main modules). Ask if it is unclear which files are relevant. Then work through the idea one question at a time: purpose first, constraints second, success criteria third.

**Check the knowledge store first.** If the project has a `docs/solutions/` directory, search for prior decisions or related problems before proposing anything. If matches are found, read them before Phase 2. Prior solutions may contain decisions, tradeoffs, or known failure modes that eliminate false starts.

**Confirm the working path before touching the filesystem.** Before creating, moving, or writing files, verify the absolute path with `pwd` or `git rev-parse --show-toplevel`. Do not assume `~/project` and `~/www/project` are the same. If the user gives a relative or ambiguous path, ask once to confirm the full absolute path.

**State all dependencies before asking for credentials.** If the task requires API keys, tokens, or third-party accounts beyond what the user named, list every dependency with a one-line explanation of why it is needed, before asking for any of them. Do not surface credential requests mid-implementation.

**Verify external tool availability before starting.** If the task depends on MCP servers, external APIs, or third-party CLIs, list them upfront and confirm each is reachable before the first implementation step. A plan that requires a tool that is not loaded is not a plan.

**Check existing work on GitHub.** Before designing, search for related issues and PRs. If `gh` is not installed, install it first.

Challenge whether it is the right problem:
- What does the user actually want to happen? Not the feature described, the outcome they care about.
- What changes if nothing is built? Is there a cheaper path to the same result?
- What already exists in the codebase that covers part of this? Map sub-problems to existing code before proposing new code.
- Does this decision hold up in 12 months, or does it create drag?

## Scope Mode

Name the mode at the start:

| Mode | When | Posture |
|------|------|---------|
| **expand** | New feature, blank slate | Push scope up. Ask what would make this 10x better. |
| **shape** | Adding to existing | Hold the baseline, surface expansion options one at a time. |
| **hold** | Bug fix, tight constraints | Scope is locked. Make it correct. |
| **cut** | Plan that grew too large | Strip to the minimum that solves the real problem. |

## Phase 2: Propose Approaches

Offer 2 or 3 options with tradeoffs and a recommendation. For each: one-sentence summary, effort, risk, two strongest reasons for and against, what existing code it builds on. Always include one minimal option and one architecturally complete option.

When comparing, ask:
- Which decisions are hard to undo? Slow down on those.
- What would cause this to fail? Design away from that first.
- What are we explicitly not building?
- Would the same result hold with less: fewer fields, fewer states, fewer APIs?

Before presenting the recommendation: attack it. Ask yourself what would make this approach fail. If the attack holds, the approach deforms, and you should present the deformed version instead. If the attack shatters the approach entirely, discard it and tell the user why.

Get approval before proceeding. If the user rejects the design, do not start over from scratch. Ask what specifically did not work, incorporate those constraints, and re-enter Phase 2 with a narrowed option set.

## Phase 3: Validate the Architecture

Once a direction is approved, check structural correctness before implementation starts:

**Scope.** Grep for existing implementations of each sub-problem. Flag anything deferrable. More than 8 files or 2 new services? Acknowledge it explicitly.

**Dependencies and data flow.** If more than 3 components exchange data, draw an ASCII diagram. Look for cycles and hidden coupling. Trace the main path, then break it: nil input, empty collection, upstream timeout, partial failure.

**Test coverage.** List every meaningful path: happy path, error branches, edge cases. List gaps with file, assertion, test type. Any bug fix without a reproducing test is not done.

**Risk.** Name every component whose loss degrades the system. Can this be rolled back without touching data? Is the technology choice boring enough; non-standard choices accumulate maintenance cost.

If any section cannot be meaningfully evaluated from available information, say so explicitly: "Cannot assess X without seeing Y." Do not guess to fill the gap.

**No placeholders in approved plans.** Before the user approves, every step must be concrete. Forbidden patterns: TBD, TODO, "implement later", "similar to step N", "details to be determined", "as needed". A plan with placeholders is not a plan. It is a promise to plan later.

## Phase 4: Confidence Check

Before handing off to implementation, score confidence on three axes:

1. **Problem understood?** Can I state in one sentence what the user actually needs and why?
2. **Approach is the simplest that works?** Is there a cheaper path I have not considered?
3. **Unknowns are resolved or explicitly deferred?** No TBDs hidden in the plan.

If any axis is low: loop back. Low on (1) returns to Phase 1. Low on (2) returns to Phase 2. Low on (3) returns to Phase 3 and names each unresolved unknown explicitly.

If all three are solid: state the confidence assessment in 2-3 sentences at the end of the approved design summary, then stop. Do not proceed into implementation.

## Implementation Protocol

Once the design is approved, enforce one behavior per cycle.

**RED**: Write the smallest test that proves the behavior is missing. Run it. It must fail for the right reason, not from a typo or missing import.

**GREEN**: Write the minimum code to pass the test. No refactor, no extras.

**REFACTOR**: Remove duplication, improve names. Re-run tests after each step.

Do not write production code before a failing test. "Small change" and "obviously works" are not exceptions.

Before claiming done:

```
Behavior:   [one sentence]
RED seen:   yes/no
GREEN seen: yes/no
Verify:     [command] -> pass/fail
```

If RED or GREEN was not observed, status is not complete.

## Gotchas

Real failures from prior sessions, in order of frequency:

- **Wrong path assumed.** Moved files to `~/project` when the repo was at `~/www/project`. Always run `pwd` or `git rev-parse --show-toplevel` before the first filesystem operation.
- **Credentials surfaced mid-build.** Asked for DashScope API key after three implementation steps. List every dependency with a one-line explanation of why it is needed, before starting.
- **Analyzed when execution was requested.** User said "帮我做" and got three options. "帮我做," "优化," "改回去" = execute immediately. No option framework.
- **Designed around a tool that wasn't available.** Planned an MCP-dependent workflow without checking if the MCP server was loaded. Verify external tool availability before the first design step.
- **Rejected design restarted from scratch.** User said the direction was wrong. Should have asked what specifically failed and re-entered Phase 2 with narrowed constraints, not a blank slate.
- **Assumed regional API variants were identical.** Shengwang (China) and Agora (International) have different endpoints, auth schemes, and supported vendors. Built against the wrong one. List all regional differences before writing integration code.
- **Added a new runtime without asking.** Followed official docs' FastAPI examples into a Next.js project, creating a Python backend nobody wanted. Translate doc examples to the user's existing stack; never add a new language or runtime without explicit approval.

## Output

For each issue found in Phase 3:
- What it is (1 sentence)
- Specific recommendation ("move X to Y because Z", not "consider refactoring")
- Fix size: small, medium, large
- Risk if ignored: low, medium, high

**Approved design summary:**
- **Building**: what this is (1 paragraph)
- **Not building**: explicit out-of-scope list
- **Approach**: chosen option with rationale
- **Key decisions**: 3-5 with reasoning
- **Unknowns**: anything needing resolution during implementation

Close with one-line status per architecture section: clear, flagged, or skipped with reason.
