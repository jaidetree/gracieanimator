# Learnings

Session memory for the Django migration. Newest first. Prune when stale.

> **Test env leak (recurring).** Local `.envrc.local` exports remote `DATABASE_URL`
> (RDS, no createdb perm → `pytest` dies "permission denied to create database")
> and `R2_*` staging vars (→ `R2_ENABLED=bool(R2_BUCKET_NAME)` flips
> `STORAGES["default"]` to S3, so FileField/ImageField tests silently upload to the
> *real* bucket — the only tell is a stray `botocore` auth `DeprecationWarning`).
> Run with the storage env stripped to exercise `FileSystemStorage` like CI:
> `env -u DATABASE_URL -u R2_BUCKET_NAME -u R2_ACCESS_KEY_ID -u R2_SECRET_ACCESS_KEY -u R2_ENDPOINT_URL -u R2_CUSTOM_DOMAIN pytest`.
> (CI has the *inverse* problem — see Slice 14.)

## In-place page-swapper / HTMX + Playwright E2E (Slice 7)

- **`hx-boost` on a wrapper + inherited `hx-select` = client swap with zero new
  server code.** Put `hx-boost="true"` plus `hx-target`/`hx-select`/`hx-swap`/
  `hx-push-url` on one `#comic-viewer` div; every `<a href>` inside is boosted and
  *inherits* those attrs (only `hx-get` is per-link, and boost supplies it from the
  href). The server re-renders the whole page; `hx-select="#comic-viewer"` extracts
  just that fragment from the full response — **no partial template, no
  HTMX-request detection, no new endpoint.** Chosen over Alpine precisely because
  the server keeps re-rendering: the chevrons' server-side prev/next `{% if %}`
  conditionals (and every Slice 6 test) stay correct after a swap. Alpine would
  need both chevrons always in the DOM, breaking the page-1-has-no-prev asserts.
- **Keep links that change *more* than the fragment OUTSIDE the wrapper.** The
  back-link and sibling (prev/next-comic) bar live outside `#comic-viewer` so they
  navigate normally; boosting them would swap only the viewer and leave a stale
  title/sibling bar.
- **A single-line `{# … #}` comment IS stripped from output** (unlike a multi-line
  one — see Slice 13). To leave a stable structural anchor for a test (e.g. proving
  the sibling bar renders *after* the wrapper closes), use an HTML comment
  `<!-- /#comic-viewer -->`, which survives.
- **Playwright E2E wiring (the non-obvious parts):** `live_server` + the
  `page` fixture needs `@pytest.mark.django_db(transaction=True)` so the factory
  rows are committed for the server thread's separate connection. Playwright's sync
  API holds an asyncio loop in the test thread, tripping Django's async guard on
  those ORM calls → set `os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")`
  (safe: the browser runs on its own thread, no real concurrent DB access). Note it
  leaks to the whole session because the e2e module is imported at *collection*
  even when deselected — harmless with no async tests. Mark `e2e` and deselect by
  default (`-m "not live and not e2e"`), mirroring `live`.
- **The no-reload proof needs a sentinel, not just URL/src asserts.** A full
  navigation also changes the URL and the image `src`, so those don't distinguish a
  swap from a reload. Set `window.__flag` *and* tag a node *outside* the wrapper
  (the `<h1>`) before the click; both surviving proves the swap was reload-free
  *and* scoped to the fragment.
- **`live_server` serves vendored static via staticfiles** (DEBUG=True under
  `APP_ENV=test` enables finders), so the vendored `static/js/htmx.min.js` loads.
  Media isn't served, but the E2E only reads the `src` attribute, never the bytes.
  Strip the R2/`DATABASE_URL` env for E2E too (factories upload images).

## Inline file attachments (Slice 18)

- **`FileField`, not `ImageField`, for "PDFs / other file types."** `ImageField`
  runs Pillow validation and silently rejects non-images. Use `FileField` with
  *no* extension `validators=`. Load-bearing test: upload a
  `SimpleUploadedFile("brief.pdf", b"%PDF…")` and assert it saves — the test a
  naive `ImageField` fails.
- **No ordering ask → plain `admin.TabularInline`, not Slice 17's sortable2.** Keep
  `file` required: an empty `extra=1` row is skipped by the formset, so it forces
  no phantom upload.

## Drag-and-drop sortable admin (Slice 17)

- **`django-admin-sortable2` fully *owns* the sort field.** Changelist
  `get_list_display` replaces the sort field with the `_reorder_` handle (or
  inserts at index 0 if absent); `get_fields` strips it from the change form; the
  inline forces it to `HiddenInput`; `save_model`/`save_new` auto-number new rows
  to the end. (This is why Slice 16's whole order-UX layer was removed.)
- **Handle-on-the-left = OMIT the sort field from `list_display`.** Keeping it makes
  sortable2 swap the handle in *in place* (mid-table); dropping it inserts
  `_reorder_` at index 0.
- **Re-add the sort field in `get_fields` for `obj is not None` only** to keep a
  typeable order input on the existing-object change form (add form omits it,
  auto-numbers). Inlines *can't* keep a numeric input — sortable2 hard-codes the
  order widget to `HiddenInput`, drag-only.
- **The sort field must NOT stay in `list_editable`** (not a displayed column, so
  an inline input has nowhere to render). `published`/`featured` coexist fine.
- **Drag only reindexes the *moved span*, not the whole collection.** `onEnd` POSTs
  `{"updatedItems": [[pk, order], …]}` for the moved rows only; gaps elsewhere
  survive. For "clean up the *entire* collection," override `_update_order`:
  `super()` then `bulk_update` every row to `1..N` by current order (`order` has no
  unique constraint).
- **Test the reorder endpoint headlessly** via `admin_client`:
  `reverse("admin:<app>_<model>_sortable_update")`, POST that JSON (GET → 405).
  Render-level checks (`class="drag handle"`, `_reorder_` before `title`,
  `name="order"` on change form) catch the wiring structural asserts miss.
- **Use `SortableTabularInline`** (not bare `SortableInlineAdminMixin` +
  `TabularInline`) — only it sets the handle row template. The inline asserts its
  parent is a `SortableAdminBase`, so the parent ModelAdmin needs
  `SortableAdminMixin`. Add `"adminsortable2"` to `INSTALLED_APPS`.

## Linter + CI (Slice 14)

- **Ruff is linter *and* Black-compatible formatter in one binary**, runs via
  existing `uv` (`uvx ruff …`). Config in `ruff.toml` (repo's one-file-per-tool
  convention) using bare `[lint]`/`[format]` tables, not `[tool.ruff.lint]`.
- **Delegate line length to the formatter; `ignore = ["E501"]`.** The `E` group
  pulls in `E501`, which the formatter won't fix on comments/strings → permanently
  red lines CI can't green. Measure with `ruff format --check` before applying;
  don't let `--fix`/`format` rewrite as an unseen side effect.
- **`extend-exclude = ["*/migrations/*"]`** — Django emits them; `ruff format`
  wanted to rewrite them otherwise.
- **CI Postgres needs an explicit TCP `DATABASE_URL` — the inverse of the local
  leak.** `config.test_settings` forces `APP_ENV=test` but base settings still read
  `DATABASE_URL`, defaulting to a unix-socket URL the `services: postgres`
  container (TCP only) can't answer. Set
  `DATABASE_URL=postgres://postgres:postgres@localhost:5432/gracie`. YAML is the
  one part unverifiable locally — confirm on first real run.
- **"Run tests then lint" = `needs: test`.** Two jobs, `lint` gated on `test`, on
  `django` push/PR only (not `main`, the legacy ClojureScript stack).

## Auto-increment order field (Slice 16) — superseded by Slice 17 for the admin UX

> Drag-and-drop replaced this layer; `OrderedAdminMixin` / `save_formset` /
> `comic_page_order.js` are gone. These Django facts still hold:

- **A `PositiveIntegerField(default=0)` renders its admin input as `value="0"`, not
  empty** (non-callable default propagates to the form field's `initial`). Client
  JS treating order as "unset" must check `current !== "" && current !== "0"`.
- **You can't prefill the always-present `extra` inline row on page load.** Setting
  `order` on an empty extra form makes `has_changed()` True, so Django runs full
  validation → "image: This field is required" blocks the save (verified: order=6
  + no image → invalid; order=0 → skipped/valid). Fix is `extra = 0`; add rows on
  demand via "Add another", which fires `formset:added`.
- **Django 5 fires a native `formset:added` event** (`event.target` is the new
  row), replacing the old jQuery version. App static is picked up by
  AppDirectoriesFinder; wire via the inline's `Media.js`.

## Admin field refinements (Slice 13)

- **Model field declaration order drives the auto-built admin change-form order**
  (when no `fields`/`fieldsets`/`form`). "Move featured below published" = reorder
  the two fields on the abstract `Project` base. Assert on `_meta.fields`, not
  `get_fields()` (which also pulls reverse relations like Comic's `pages`).
- **Reordering fields generates no migration** — pure source-order edit, no schema
  delta. Only the `published` `default=True` flip emitted `AlterField`s.
- **`list_editable` column order is cosmetic — `list_display` drives the changelist
  layout.**

## Homepage featured grid (Slice 11)

- **An ordered registry of `(model, label, reverse_lazy(url))` is the seam for a
  cross-model, partially-built selection.** `FEATURED_TYPES` holds built types plus
  a commented-out Storyboard entry (model not built until #10);
  `featured_projects()` loops it and skips empties — a missing/unfeatured type
  simply contributes nothing (one mechanism for both cases). The
  "combines four models" / storyboard-first ACs are *not* done until #10 lands.
- **`reverse_lazy` in the tuple** is import-safe (defers resolution), so the
  registry carries the URL value, not a name to `reverse()` per request.
- **The grid labels the content *type*, not the piece** (visitors navigate to
  sections). Tests that need *which* piece was selected assert on its rendition
  URL, since the title isn't rendered.
- **`.first()` on `filter(published=True, featured=True)` makes "one per type"
  deterministic** via `Project.Meta.ordering = ["order", "title"]`.
- **`thumbnail_url` isn't uniformly square across types** (image types → 400²
  `ResizeToFill`; Comic → fit-width portrait). Normalize with `aspect-square
  object-cover` on the `<img>` — no model change.

## Comic type / multi-image projects (Slice 6)

- **"Full resolution in detail" means the original, not a capped rendition.** The
  detail view serves `page.image.url` directly (only a small `grid_image` rendition
  exists, for the index). This intentionally breaks the gallery's "serve rendition
  not original" rule — that was a per-surface width choice, not a global ban. Detail
  test asserts the original IS served.
- **A multi-image project = parent `Project` + child rows, not an array field.**
  `Comic(Project)` carries no media; ordered `ComicPage` (FK + `order`,
  `Meta.ordering = ["order", "id"]`) holds images. `Comic.derived_thumbnail_url` →
  first page's `grid_image.url` (None when no pages).
- **Page 1 has two URLs by design.** One view bound to `/comics/<slug>/` (page
  defaults to 1) and `/comics/<slug>/page/<int:n>/`; page 1's canonical URL is the
  bare one. `n` outside `1..count` raises `Http404`. Tests pin exact prev/next
  hrefs at both boundaries.

## oembed boundary (Slice 5)

- **Single HTTP seam with stdlib `urllib`, mocked at the imported name.**
  `portfolio/oembed.py` is the one place provider HTTP happens (ADR-0002). Tests
  patch `portfolio.oembed.urlopen` (the name as imported, not
  `urllib.request.urlopen`). `urllib` raises `HTTPError` (a `URLError` subclass) for
  non-2xx, so one `except URLError` covers network-down and provider-4xx/5xx as
  `OEmbedError`.
- **Provider quirks (from legacy stack, confirm against live):** Vimeo's
  `thumbnail_url` comes back extension-less and 404s without `.jpg`; Vimeo gates
  oembed on a whitelisted `Referer`
  (`https://gracieanimator.squarespace.com`). Speakerdeck 403s the default
  `Python-urllib` User-Agent → needs a browser-like UA on every request
  (caught by opt-in `test_oembed_live.py`, `-m live`; deselected by default). A live
  failure often means a fixture URL rotted, not a regression.

## Model abstraction (Slice 4)

- **imagekit `ImageSpecField`s are descriptors, not DB columns** — never appear in
  migrations. To DRY two identical types (ADR-0003), extract an abstract
  `ImageProject(Project)` base holding renditions (`gallery_image`,
  `thumbnail_rendition`) + `derived_thumbnail_url`, but **keep the `image` field on
  each concrete subclass** (own `upload_to` namespace, migration-free). Unifying
  `image` onto the base would emit an `AlterField` rewriting the upload path. Verify
  with `makemigrations --dry-run` (expect only the new model's migration).

## Storage / R2 (Slice 3)

- **Gate media storage on `R2_BUCKET_NAME` presence, not `APP_ENV`.** Switching
  `STORAGES["default"]` to S3 unconditionally breaks every test/local dev (factories
  saving an `ImageField` → network call, no creds). Local FS stays default. Prod
  guard: `APP_ENV=production` + no bucket → `ImproperlyConfigured`.
- **imagekit renditions follow the `"default"` storage alias automatically**
  (`IMAGEKIT_DEFAULT_FILE_STORAGE` → `DEFAULT_STORAGE_ALIAS`). No extra config.
- **R2 public serving requires `R2_CUSTOM_DOMAIN`** (mapped domain or `pub-*.r2.dev`)
  + bucket public access. The account endpoint
  (`<acct>.r2.cloudflarestorage.com`) only answers SigV4-signed requests, so with
  `querystring_auth=False` and no custom domain, `url()` yields an unsigned URL that
  401s on public GET — `<img src>` won't load.
- **Test import-time settings branches in a clean subprocess** with a controlled env
  (`portfolio/tests/test_storage.py`) — settings decides the backend at import time,
  so a conftest fixture / `override_settings` runs too late.
