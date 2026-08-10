---
name: slice
description: >-
  Use this skill when the user invokes /slice or wants to take one tracked
  vertical slice end-to-end: move it to In Progress, implement it, commit, and
  move it to Review. Trigger on "/slice <issue>", "do slice N", "work issue N",
  or "ship slice N".
---

# Slice

Take one tracked slice of the Gracie portfolio site end-to-end: In Progress →
implement → commit → Review.

Requires an issue argument (a `NN-slug` stem or number). Resolve it under
`.gracie-vault/Projects/gracie-portfolio/issues/**` by filename stem (zero-pad
numbers to two digits) — the folder it sits in is its current dev state. If no
argument, or the target is ambiguous, stop and ask.

## Steps

1. Read a knowledge summary: `scan-knowledge.sh .gracie-vault/Knowledge` (from
   the `knowledge` skill); surface the most relevant points.
2. Read the slice file, plus its spec (`.gracie-vault/Projects/gracie-portfolio/Spec.md`,
   if present), `.gracie-vault/Domain/CONTEXT.md`, and any `.gracie-vault/ADRs`
   it touches. Stop if the issue isn't found — report what failed.
3. Move the slice file (from `Ready` or, if `/afk` dispatched it straight from
   `Backlog`, from `Backlog`) → `In Progress` (folder = dev state; see
   `docs/agents/issue-tracker.md`).
4. `/implement` the slice as specified. Follow project conventions: one Django
   app per bounded concern (`portfolio`, `pages`, `branding`, `core`,
   `common`), scaffolded via `manage.py startapp`/management commands rather
   than hand-written where a generator fits; match the live reference site's
   DOM structure and Tailwind classes at https://gracieanimator.fly.dev when
   building or changing views/templates. Write/update tests at the seams the
   issue names.
5. Verify: `make build` and `make lint`, then `make test`. On failure, fix and
   **goto 4**.
6. Commit: `/commit <slice description>`. Skip if nothing to commit; never
   commit partial or failing work.
7. Move the slice file `In Progress` → `Review` — this signals it awaits human
   testing. Check off the acceptance-criteria `- [ ]` boxes that now hold. Only
   a human moves it to `Done`.
8. Run `/knowledge` to record findings — what worked, what broke, and
   non-obvious domain facts — as notes in `.gracie-vault/Knowledge/`. Be
   selective.
9. Report a list of manual testing steps for humans.
