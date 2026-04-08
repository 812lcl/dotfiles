---
name: learn
description: "Invoke when diving deep into an unfamiliar domain, preparing a research article, or turning collected sources into publishable output. Runs a six-phase workflow: collect, digest, outline, fill in, refine, publish. Not for quick lookups or single-file reads."
version: 3.2.0
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - WebSearch
  - AskUserQuestion
---

# Learn: From Raw Materials to Published Output

Deep research structured like engineering work. Six phases, each with a clear role for you and a clear role for AI.

The measure of learning is not how much you read. It is how much you produce. Input that never becomes output is just consumption.

AI is a tool in this process, not a replacement for your thinking. Never let AI read for you, decide for you, or write in your voice without your direction. The moment you outsource the thinking, the learning stops.

## Choose Your Mode

Before starting, use AskUserQuestion to confirm which mode fits the goal:

| Mode | Goal | Entry point | Exit point |
|------|------|-------------|------------|
| **Deep Research** | Understand a domain well enough to write about it | Phase 1 | Phase 6: publish |
| **Quick Reference** | Build a working mental model fast, no article planned | Phase 2 | Phase 2: cut and keep notes |
| **Write to Learn** | Already have materials, want to force understanding through writing | Phase 3 | Phase 6: publish |

If the user is unsure, suggest Quick Reference. Do not proceed until mode is confirmed.

## Phase 1: Collect

Gather only high-quality primary sources. For a technical domain this means: recent papers that introduced key ideas, official model and product blogs from the labs, posts from the people who built the thing, university course materials from the last two years, and canonical "build it from scratch" repositories.

Not summaries. Not explainers. Not "top 10 things you need to know." Sources.

For each source: download it, convert to Markdown, clean, and file it into a structured research directory organized by sub-topic.

```bash
# Convert a URL to Markdown and save it
# Use /read for individual pages
# For bulk work: automate with curl + r.jina.ai or a download script
```

The goal at the end of Phase 1: a local, organized repository of raw materials.

For a blog post or article, 5-10 strong sources is usually enough. For a deep technical survey, 15-20. If you have been collecting for an hour and have not started reading, you are collecting to avoid the harder work. Stop and move to Phase 2.

## Phase 2: Digest

Work through the materials yourself. For each piece:

- If you understand it: read it fully, keep what is good, delete what is not.
- If you do not understand it: ask Claude to explain the specific part that is unclear. For dense technical content, ask for a Chinese translation. Do not ask for a summary of the whole thing.
- If there is code: run it locally if possible. If not, read the structure and understand what each part does.

At the end of this phase, cut roughly half of what you collected. If you cannot decide what to cut, the material was not strong enough.

For key concepts, try cutting across multiple angles: how did this idea evolve historically? What is the opposite claim? What does it look like in practice vs. in theory? What breaks if you remove it? This kind of multi-dimensional interrogation builds a real mental model, not just a definition.

For key claims and frameworks, apply three-layer verification before including them in your outline:

1. **Cross-domain recurrence.** Does this idea appear in at least two different contexts from the same source? A claim that shows up in one talk is a quote. A claim that appears in books, interviews, and decisions is a belief.
2. **Generative power.** Can you use this framework to predict what the source would say about a new problem they have not addressed? If yes, it is a real mental model. If not, it is a surface observation.
3. **Distinctiveness.** Is this specific to this source, or would any expert in the field say the same thing? Generic wisdom is not worth distilling.

A claim that passes all three belongs in your outline. One that passes only one is background material. Zero passes: cut it.

For fields with a research lineage, trace the intellectual genealogy: what problem was the foundational paper or idea responding to? What did it critique or improve on? Follow that chain backward two or three steps, then look forward at what built on top of it. Understanding a field as a sequence of problems being passed forward is more durable than understanding it as a set of current facts.

Claude's role here: explain, translate, answer specific questions. Not summarize or evaluate on your behalf.

## Phase 3: Outline

Once you have a working mental model of the domain, write an outline for the article.

The outline must answer: what do you want to say, and what does your reader need to know to follow it? These are not the same question. Know your reader's level and write for that level, not above it.

For each section in the outline: note the source materials it draws from. If a section has no sources, either it does not belong in the article or you need to find the source.

The outline is a contract with yourself. Do not start filling it in until it is solid.

## Phase 4: Fill In

Work through the outline section by section. This is the repetition phase: revisiting material you already processed, synthesizing it into continuous prose, filling gaps as you find them.

You will end up with a long, somewhat rambling draft. That is correct. Do not edit while writing. Get it all down first.

If a section is hard to write, it usually means the mental model is still weak in that area. Go back to Phase 2 for that sub-topic rather than forcing through. The outline may need to change, and that is fine.

## Phase 5: Refine with AI

Now hand the draft to Claude with a specific brief:

- Remove redundant and verbose passages without changing the meaning or your voice
- Flag places where the argument does not flow
- Identify gaps: places where a concept is used before it is explained, or where a claim needs a source

Work through the suggestions yourself. Accept, reject, or modify each one. Do not accept blindly. This phase often surfaces things you missed in Phase 2, which means more learning.

Before accepting Claude's edits, run `/write` on the refined draft to strip any AI patterns that crept in during the refinement process.

## Phase 6: Self-Review and Publish

Read the entire article yourself, not with AI. Read it as your target reader would: linearly, without jumping back.

Mark everything that feels off: unclear sentences, abrupt transitions, sections that drag. Fix them. Read again. Two full passes is the minimum.

When it reads clean from start to finish: publish it.

One concern to set aside: "what if no one reads it." If the content has substance, readers will find it. That concern is not a reason to skip publishing. It is a reason to make sure the content has substance.

## At Any Phase: What to Ask Claude

| Situation | Useful prompt |
|-----------|---------------|
| Something is unclear | "Explain [concept] to someone who knows [adjacent field] but not this one" |
| Dense technical paper | "Translate this section to Chinese, keep technical terms in English" |
| Evaluating a source | "What is the main claim here, and what evidence supports it?" |
| Outline feedback | "What is missing from this outline for a reader who knows [level]?" |
| Draft refinement | "Cut the redundancy from this section without changing my voice or meaning" |
| Gap detection | "What would a reader need to know before reading this section?" |

## Red Lines

- Do not ask Claude to summarize a paper you have not read. Read it yourself.
- Do not let Claude write sections of the article from scratch. Fill them in yourself, then refine.
- Do not skip Phase 6 because "AI already reviewed it." AI read it for fluency. You need to read it for truth.
