# Fetch and cache oembed at save time

Storyboard videos (Vimeo/YouTube) and decks (Speakerdeck) are authored as plain
provider URLs. When a storyboard is saved, we call the provider's oembed API
once and cache the resulting embed HTML, width/height (for aspect-ratio
padding), and — for videos — the poster image, onto the related rows. Public
pages render the cached values; no oembed calls happen at request time.

## Considered Options

- **Fetch at request time** — rejected: slow, fragile, hammers providers.
- **Paste embed HTML manually** — rejected: more manual work, requires
  sanitizing untrusted HTML, and yields no poster image for thumbnails.
- **Construct iframes ourselves from the URL** — rejected: loses
  provider-supplied dimensions and the video poster, and Speakerdeck is hard to
  construct by hand.

## Consequences

- A model save performs network I/O; failures must be handled gracefully (keep
  the URL, allow re-save) rather than blocking the admin.
- The cached embed HTML/dimensions/poster are denormalized fields — refetched on
  save, not kept live with the provider.
- The fetched video poster doubles as the storyboard thumbnail fallback
  (see ADR-0003).
