## Agent skills

### Project

This is a greenfield Django + Postgres rebuild of Gracie's portfolio site, replacing the legacy ClojureScript/Notion/nbb stack. The two stacks share one repo (`jaidetree/gracieanimator`): the rebuild lives on the `django` branch, while `main` holds the legacy implementation as a reference.

The original PRD and its vertical-slice sub-issues shipped and closed as GitHub issues #2–#37 (kept on GitHub for history only — see `docs/agents/issue-tracker.md` for where active work lives now). Design decisions live in the vault: `.gracie-vault/Domain/CONTEXT.md` (domain glossary) and `.gracie-vault/ADRs/`.

### Live reference site

The current production site is live at **https://gracieanimator.fly.dev**. It runs the legacy stack and is the source of truth for **markup and UI** — when rebuilding a page or component, fetch the matching live URL and match its DOM structure, Tailwind classes, and visual layout. Example: a comic detail page is `https://gracieanimator.fly.dev/comics/<slug>/`. Prefer this over the `main`-branch ClojureScript source when checking how something should look, since it reflects the deployed markup.

### Scaffolding

Prefer Django's built-in generators and scaffolding (`manage.py startapp`, `startproject`, management commands) over hand-writing files; they produce idiomatic, convention-correct structure with less drift. Only write files raw when no generator fits.

### Project vault

Vault at `.gracie-vault/`, home for knowledge notes, ADRs, and reference material. See `docs/agents/vault.md`.

### Issue tracker

Vault at `.gracie-vault/Projects/gracie-portfolio/`. Move issues between the `Backlog / Ready / In Progress / Review / Done / Archived` folders as work progresses; humans move to Done. See `docs/agents/issue-tracker.md`.

### Triage labels

Roles applied as frontmatter `tags:`: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: glossary at `.gracie-vault/Domain/CONTEXT.md`, ADRs at `.gracie-vault/ADRs`. See `docs/agents/domain.md`.
