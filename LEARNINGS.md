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

## Storyboard public views (Slice 10)

- **The compiled Tailwind CSS (`static/css/stylesheet.css`) is a committed build
  artifact that regenerates from template classes.** Adding new utility classes
  in a template (`aspect-[3/2]`, `sticky`, `col-span-12`, `space-y-*`,
  `text-white/50`, `hover:bg-black/20`, …) produces an unstaged diff in that
  one-line minified file (a watcher rebuilt it here). Commit it *with* the
  templates or the new styles won't apply in prod. It's not noise — diff it to
  confirm only expected classes were added.
- **"Grids use small renditions" only reaches a *manual* thumbnail.** Storyboard
  has no `image` field; its auto-thumbnail is the first video's external oembed
  `poster_url`, which can't be renditioned. So `grid_thumbnail_url` returns a
  square `thumbnail_rendition` (ImageSpecField on `thumbnail`, descriptor → no
  migration) only `if self.thumbnail`, else the external poster. Test the
  rendition path exactly like comics: rendition URL present, full `thumbnail.url`
  absent (needs real JPEG bytes so imagekit can resize; run env-stripped).
- **Detail must render independently of video presence.** A thumbnail-only
  storyboard is valid (Slice 8 formset rule), so `get_object_or_404` and the
  title/body/nav can't sit inside the video loop. Guard the responsive embed
  wrapper with `{% if video.embed_html %}` — an unreachable video has
  `embed_html=""` and `embed_width/height=None`, so an unguarded wrapper emits an
  empty `<iframe>` and a bare `padding-bottom: %`.
- **Aspect-ratio box from cached dims with `widthratio`, no view math:**
  `style="padding-bottom: {% widthratio embed_height embed_width 100 %}%"`. Safe
  only inside the `embed_html` guard (dims are cleared to None together with the
  html).
- **Asserting "no request-time oembed" needs the spy installed *after* the rows
  exist.** The autouse `stub_oembed` already patches `fetch` (and `save()` calls
  it on create), so build the storyboard+video first, *then*
  `monkeypatch.setattr(oembed, "fetch", Mock())`, GET, and `assert_not_called()`.
- **Homepage storyboard entry is now unblocked** — Slice 10 created the
  `storyboard_gallery` URL, so `FEATURED_TYPES`'s commented Storyboard line can
  be enabled (Slice 11 scope; left untouched here). Supersedes the Slice 8 note
  that the homepage featured grid "stays deferred past #10."

## Storyboards authoring + oembed-on-save (Slice 8)

- **The oembed cache lives on the child row's `save()`, not the admin.** Each
  `StoryboardVideo`/`Deck` resolves its URL through `oembed.fetch` in `save()`
  and caches `embed_html`/dims (+ video `poster_url`). This is the single seam
  the "model-save-seam tests" target — no admin needed to exercise it.
- **Guard re-fetch with `_needs_oembed`: resolve only when unresolved (new row
  or prior failure) or the URL changed.** Detect a URL change by comparing
  `self.url` to the DB value (`objects.filter(pk=…).values_list("url")`). Gives
  both "fetched once" (no-op re-save makes no call) *and* recovery (a failed
  fetch left `embed_html` empty, so a re-save retries).
- **On `OEmbedError`, CLEAR the cache, don't leave it.** Keeping the old embed
  after the URL changed serves a stale iframe/poster against a gone URL — and
  the guard would never refetch it (non-empty html + unchanged url). Clearing is
  safe because you only reach resolution when the cache is empty or url changed.
  Caught only by a "change URL to an unreachable provider" test; the create-fail
  path (cache already empty) hides it.
- **"At least one X child" can't be a model rule.** The parent saves before its
  inline children, so `self.videos` is empty during model validation. Enforce in
  the inline's `BaseInlineFormSet.clean` (count forms with `cleaned_data` and not
  `DELETE`). Test by driving the real bound formset (management-form data + N
  rows), incl. an INITIAL row marked `DELETE` for the "deleted last video" path.
- **A custom formset on a *sortable* inline must extend
  `adminsortable2.admin.CustomInlineFormSet`, not `BaseInlineFormSet`** — the
  sortable inline injects a `default_order_direction` kwarg the plain base
  rejects (`TypeError`). And `CustomInlineFormSet.__init__` takes
  `default_order_direction`/`_field` as its *leading positional* args, so in
  tests pass `data=` by keyword or it gets swallowed and the formset is unbound.
- **Three `SortableTabularInline`s on one parent works** (extra=0 each); the
  repo previously only had one (ComicPage). Verified by GETting the add form
  (all three `*-TOTAL_FORMS` present) and a full admin add/change POST.
- **Autouse `stub_oembed` in conftest keeps factory-built media off the
  network** (`save()` fetches on create, where `pk is None` so it always
  resolves — you can't pre-seed `embed_html` to skip it). The `test_oembed`
  modules opt out (`"test_oembed" in request.module.__name__`) to exercise the
  real `fetch` via the `urlopen` seam.
- **`extra=0` on the inlines** reaffirms the Slice-16 trap: a `default=0` order
  field makes an always-present blank row look "changed" → spurious required
  errors. Add rows on demand.
- **Homepage featured grid stays deferred past #10** — `FEATURED_TYPES` needs
  the `storyboard_gallery` *public* URL (a later slice), so the Slice-11
  "storyboard-first" AC still isn't satisfied by the model/admin alone.

## In-place page-swapper / Alpine.js + Playwright E2E (Slice 7, migrated)

- **Pure `src`-swap eliminates layout shift; DOM-fragment swap does not.**
  The original HTMX approach fetched a full page and swapped `#comic-image` out of
  the DOM — the image container collapsed while the incoming image loaded, causing
  a visible jump. Replacing `src` in place (Alpine `:src="currentImage"`) avoids
  any layout recalculation; the container never changes size.
- **Alpine `comicViewer(initialImage, initialPage, pages[])` pattern.** Mount on
  `#comic-viewer` with `x-data`; pass the full pages array (each `{imageUrl, href}`)
  from the Django template loop — all URLs are available server-side. `goTo(index)`
  sets `currentImage`, updates `currentPage`, calls `history.pushState`. No new
  endpoint, no server round-trip for image navigation.
- **Chevron visibility: `x-show` + inline `style` seeds no-JS initial state.**
  Both chevrons are always in the DOM; `x-show="currentPage > 1"` /
  `x-show="currentPage < pages.length"` control them reactively after any
  client-side navigation. For the no-JS / pre-Alpine render, seed with
  `style="{% if page_number == 1 %}display:none{% endif %}"` so the initial paint
  is correct without JS. Alpine overrides it on init. (The earlier HTMX version
  used server-side `{% if has_previous %}` conditionals, which can't update after
  a client-side nav — that's why we always render both chevrons now.)
- **Keep links that navigate OUTSIDE the viewer outside `#comic-viewer`.** The
  sibling (prev/next-comic) bar lives outside so it does a full navigation rather
  than an Alpine-intercepted swap.
- **A single-line `{# … #}` comment IS stripped from output.** To leave a stable
  structural anchor for a test (e.g. proving the sibling bar renders *after* the
  wrapper closes), use an HTML comment `<!-- /#comic-viewer -->`, which survives.
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
- **`x-show` keeps the element in the DOM (display:none); `x-if` removes it.**
  Playwright's `to_have_count(0)` fails with `x-show` — use `to_be_hidden()` instead.
  (`to_be_hidden()` passes whether the element is absent OR `display:none`.)
- **`live_server` serves vendored static via staticfiles** (DEBUG=True under
  `APP_ENV=test` enables finders), so the vendored `static/js/alpine.min.js` loads.
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
