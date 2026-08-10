# A separate Django model per project type

The four project types (Storyboard, Comic, Illustration, Sketchbook Sample) are
modeled as distinct Django models sharing an abstract base for the common fields
(title, slug, order, featured, published), rather than a single `Project` table
with a `type` column and many nullable type-specific fields.

## Considered Options

- **Single Project model + type field** — mirrors the old ClojureScript shape
  and makes "all projects" queries trivial, but produces nullable-field sprawl
  and an admin form cluttered with fields irrelevant to the current type.

## Consequences

- Each admin form shows only the fields relevant to its type, and type-specific
  relations (comic pages, storyboard videos/decks/PDFs) model cleanly as inlines.
- Cross-type views (e.g. the homepage's one-featured-per-type) must query each
  model and combine results rather than filtering one table.
- Illustration and Sketchbook Sample are structurally identical but kept as
  separate models because they are distinct display groupings.
