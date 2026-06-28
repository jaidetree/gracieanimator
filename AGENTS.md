## Agent skills

### Project

This is a greenfield Django + Postgres rebuild of Gracie's portfolio site, replacing the legacy ClojureScript/Notion/nbb stack. The two stacks share one repo (`jaidetree/gracieanimator`): the rebuild lives on the `django` branch, while `main` holds the legacy implementation as a reference.

The PRD and primary source of truth is **GitHub issue #2**, broken into vertical-slice sub-issues #3–#15 (labeled `ready-for-agent`). Consult issue #2 when scoping or validating work against the success criteria. Design decisions live in `CONTEXT.md` (domain glossary) and `docs/adr/`.

### Live reference site

The current production site is live at **https://gracieanimator.fly.dev**. It runs the legacy stack and is the source of truth for **markup and UI** — when rebuilding a page or component, fetch the matching live URL and match its DOM structure, Tailwind classes, and visual layout. Example: a comic detail page is `https://gracieanimator.fly.dev/comics/<slug>/`. Prefer this over the `main`-branch ClojureScript source when checking how something should look, since it reflects the deployed markup.

### Scaffolding

Prefer Django's built-in generators and scaffolding (`manage.py startapp`, `startproject`, management commands) over hand-writing files; they produce idiomatic, convention-correct structure with less drift. Only write files raw when no generator fits.

### Issue tracker

Issues are tracked in GitHub Issues via the `gh` CLI; external PRs are not a triage surface. Progress lives on project board #7 — move issues to **In progress** when starting and **In review** when done (humans move to Done). See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
