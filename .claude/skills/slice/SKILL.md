---
name: slice
description: >-
  Use this skill when the user invokes /slice or wants to take one tracked
  vertical slice end-to-end: move it to In progress, implement it, commit, and
  move it to In review. Trigger on "/slice <issue-number>", "do slice N", "work
  issue N", or "ship slice N".
---

# Slice

Take one tracked slice end-to-end: In progress → implement → commit → In review.

Requires an issue number argument. If none given, stop and ask for one.

## Steps

1. Read `LEARNINGS.md` if it exists; surface the most relevant points.
2. Read the slice: `gh issue view <n> --comments`, plus any PRD/spec it
   references. Stop if the issue isn't found — report what failed.
3. Move the issue to **In progress** (per the issue-tracker doc named in
   `AGENTS.md`).
4. Implement: read existing patterns near the change, then implement the slice
   as specified. Write/update tests.
5. Run tests + lint. On failure, fix and **goto 4**.
6. Commit: `/commit <slice description>`. Skip if nothing to commit; never
   commit partial or failing work.
7. Move the issue to **In review** (per the issue-tracker doc) — this signals it
   awaits human testing. Only a human moves it to Done.
8. Run `/update-learnings` to capture what worked, what broke, and non-obvious
   domain facts. Be selective.
