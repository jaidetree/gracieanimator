# Learnings

Session memory for the Django migration. Newest first. Prune when stale.

## Linter + CI (Slice 14)

- **Ruff is the whole toolchain: linter *and* Black-compatible formatter in
  one binary.** It natively understands the `E402/F401/F403` codes already in
  the codebase's `# noqa`, and installs via the existing `uv` (`uvx ruff …`,
  no project install needed to measure). Config lives in `ruff.toml` (not
  `pyproject.toml`) to match the repo's one-file-per-tool convention
  (pytest.ini) and avoid implying this is a packaged project. `ruff.toml` uses
  bare `[lint]`/`[format]` tables — not the `[tool.ruff.lint]` nesting a
  pyproject needs.
- **Delegate line length to the formatter; ignore `E501`.** Selecting the `E`
  group pulls in `E501` (line-too-long), which the formatter deliberately
  won't fix on comments/strings — so with `E501` on, those lines stay red and
  CI can't go green without manual rewraps. Ruff's *default* select already
  omits `E501` for this reason. `ignore = ["E501"]` kept the entire lint diff
  to one unused import; the only churn was `ruff format` reflowing 11
  hand-authored files (measured first with `ruff format --check` before
  applying — don't let `--fix`/`format` rewrite as an unseen side effect).
- **Exclude generated migrations from both lint and format** via top-level
  `extend-exclude = ["*/migrations/*"]`. Django emits them; `ruff format`
  wanted to rewrite 5 of them otherwise. With them excluded the format set
  drops from 17 → 11 files.
- **CI Postgres service needs an explicit TCP `DATABASE_URL` — the inverse of
  the local `.envrc.local` problem.** Locally the leak is too *much* env
  (remote `DATABASE_URL` clobbering the socket default); in CI the danger is
  too *little* — `config.test_settings` forces `APP_ENV=test` but base settings
  still read `DATABASE_URL`, defaulting to a unix-socket URL the GitHub
  `services: postgres` container (TCP only) can't answer. The `test` job must
  set `DATABASE_URL=postgres://postgres:postgres@localhost:5432/gracie`. The
  YAML is the one part unverifiable locally — confirm on the first real run.
- **"Run tests then lint" = `needs: test`.** Two jobs, `lint` gated on `test`,
  triggered on `django` push/PR only (not `main`, the legacy ClojureScript
  stack whose `deploy.yml` is left untouched). Scoped to Python/Ruff; the lone
  JS file and templates are out-of-scope follow-ups, not eslint/djlint creep.

## Auto-increment order field (Slice 16)

- **A `PositiveIntegerField(default=0)` renders its admin form input as
  `value="0"`, not empty** — the non-callable model default propagates to the
  form field's `initial`. So client JS that prefills order must treat `"0"` as
  "unset" (`current !== "" && current !== "0"`), mirroring the server's
  `order == 0` sentinel. A naive `value !== ""` guard bails on every row and the
  prefill is silently dead — the saved data still looks right because the
  server backstop does the work, so the broken JS hides in plain sight.
- **Auto-increment lives in the admin (`save_model` + `save_formset`), not
  `model.save()`.** `default=0` can't tell "user typed 0" from "unset", and
  factories/tests create rows with explicit `order=0`; computing in `save()`
  would clobber them. Admin-layer keying on *new object + order==0* leaves all
  factory-driven tests (which never touch the admin) untouched, needs no
  migration, and matches the "Order Field UX" framing.
- **Next order = `max(order)+1` over ALL rows of the type, not published-only.**
  The issue said "count of published items + 1", but maxing over published-only
  can collide with a hidden item's order (unpublished at 2 + one published → 2);
  count+1 also collides on any delete-gap. Max-over-all + 1 slots cleanly at the
  end. ComicPage numbering is scoped per comic and assigned in form order so
  several rows added at once get distinct increasing values.
- **Pre-fill the parent add form via `ModelAdmin.get_changeform_initial_data`,
  not JS.** It seeds the add view's initial values server-side, so the `order`
  field shows `max+1` instead of the model default 0. Unlike an inline's empty
  extra row, the main add form is always a real submitted form, so seeding its
  initial carries no has_changed/validation trap. `setdefault("order", …)` lets
  an order passed in the URL still win; `save_model` remains the backstop.
- **You can't prefill the always-present `extra` inline row on page load.**
  Setting `order` on an otherwise-empty extra form makes `has_changed()` True,
  so Django stops skipping it and runs full validation → "image: This field is
  required" blocks the save (verified: order=6+no image → invalid; order=0 →
  valid/skipped). Fix is `extra = 0` — no blank row sits showing 0, and pages
  are added on demand via "Add another", which fires `formset:added` so the
  prefill runs on a row the editor actually means to fill.
- **Django 5 fires a native `formset:added` event** (`event.target` is the new
  row), replacing the old jQuery `formset:added` with a `$row` arg. App static
  (`portfolio/static/portfolio/…`) is picked up by AppDirectoriesFinder; wire it
  via the inline's `Media.js`.
- **Testing `save_formset` without the admin client:** build the same bound
  `inlineformset_factory` formset the admin would (management-form keys + a
  generated JPEG per row), then call `admin.save_formset(None,
  SimpleNamespace(instance=comic), formset, change=False)` — it only uses
  `form.instance`. Avoids superuser-auth/URL/multipart fragility while
  exercising the real numbering path.

## Admin field refinements (Slice 13)

- **Model field declaration order drives the admin change-form order when the
  ModelAdmin sets no `fields`/`fieldsets`/`form`.** "Move featured below
  published" in the form was achieved by reordering the two fields on the
  abstract `Project` base — the auto-built form follows `_meta.fields`. So the
  ordering test asserts on `_meta.fields` (not `get_fields()`, which also pulls
  in reverse relations like Comic's `pages`).
- **Reordering fields generates no migration; only the `default` change did.**
  Moving `published` above `featured` is a pure source-order edit with no schema
  delta, so `makemigrations` emitted only the three `AlterField`s for the new
  `default=True`. Field position isn't tracked in migration state.
- **The `published` default flips to True because the toggle is mostly used to
  *unpublish* later.** New entries are live by default; the rare draft unchecks
  it. Existing factories already set `published=True` explicitly, so the default
  change broke no published-filtering tests.
- **`list_editable` column order is cosmetic — `list_display` drives the
  changelist column layout.** Both were reordered for consistency, but only the
  `list_display` reorder is load-bearing.

## Homepage featured grid (Slice 11)

- **An ordered registry of `(model, label, reverse_lazy(url))` is the seam for a
  cross-model, partially-built selection.** The homepage selects one
  featured+published piece per type ordered storyboards → illustrations →
  sketchbook → comics, but the Storyboard model doesn't exist yet (Slice 8 / #10
  still open). `FEATURED_TYPES` holds the three built types plus a commented-out
  predicted Storyboard entry; `featured_projects()` loops it and skips empties.
  Storyboards slot in by uncommenting one line when #10 lands — so the slice
  ships 3-of-4 honestly without faking the missing model. The "combines the four
  models" / storyboard-first-ordering ACs are *not* fully satisfied until then;
  don't tick them as done.
- **`reverse_lazy` puts the section URL directly in the registry tuple.** There's
  no importable URL object in Django, but `reverse_lazy("name")` is import-safe
  (defers resolution), so the tuple carries the URL value itself rather than a
  name the view must `reverse()` per request.
- **The grid labels the content *type*, not the piece.** Visitors navigate to
  sections, so each cell shows "Illustrations" / "Comics" etc. (the registry
  label), with the featured piece supplying only the thumbnail image. Tests that
  need to distinguish *which* piece was selected (one-per-type) assert on the
  chosen piece's rendition URL, since the piece title isn't rendered.
- **"Falls back gracefully when a type has no featured piece" drops out of the
  registry, it isn't a separate branch.** A type with no eligible piece (or a
  type not yet in the registry at all) simply contributes nothing to the list —
  same mechanism covers both "no featured yet" and "model doesn't exist".
- **`.first()` on `filter(published=True, featured=True)` makes "one per type"
  deterministic for free** via `Project.Meta.ordering = ["order", "title"]` — the
  lowest-`order` featured piece wins, so several featured pieces of one type need
  no extra tie-break flag.
- **`thumbnail_url` is not uniformly square across types, so normalize in CSS.**
  Image types give a 400² `ResizeToFill` square; Comic gives a fit-width portrait
  (`cover.grid_image`, `ResizeToFit(600)` on tall pages). `aspect-square
  object-cover` on the `<img>` keeps the grid even with no model change — the
  square treatment `THUMBNAIL_SIZE`'s comment already anticipated for this surface.

## Comic type / multi-image projects (Slice 6)

- **"Full resolution in detail" means the original, not a capped rendition.**
  AC#5's contrast is rendition-vs-full, not small-vs-large rendition. A
  `ResizeToFit(CONTAINER_WIDTH)` rendition downscales most comic pages, so the
  detail view serves `page.image.url` directly; only a small `grid_image`
  rendition exists (for the index). This *breaks* the gallery's "serve rendition
  not original" rule — that rule was a per-surface display-width choice (Slice
  3/4), not a global ban, and originals serve fine from the same storage. So the
  detail test asserts the original IS served, the opposite of
  `test_gallery_serves_rendition_not_original`.
- **A multi-image project = parent `Project` + child rows, not an array field.**
  `Comic(Project)` carries no media; an ordered `ComicPage` (FK + `order`,
  `Meta.ordering = ["order", "id"]`) holds the images. This buys an authored-
  order admin `TabularInline` and per-page imagekit renditions for free. The
  auto-thumbnail fallback chains through the children:
  `Comic.derived_thumbnail_url` → first page's `grid_image.url` (None when no
  pages), reusing the `Project.thumbnail_url` manual-wins property unchanged.
- **Page 1 has two URLs by design.** Detail is served by one view bound to both
  `/comics/<slug>/` (page defaults to 1) and `/comics/<slug>/page/<int:n>/`;
  `/page/1/` resolves identically, but page 1's *canonical* URL is the bare one,
  so the prev link from page 2 targets `/comics/<slug>/`. Bounds (`n` outside
  `1..count`) raise `Http404`. Tests pin the exact prev/next hrefs at both
  boundaries, not just the happy middle page.

## oembed boundary (Slice 5)

- **Single HTTP seam with stdlib `urllib`, mocked at the imported name.** The
  oembed client (`portfolio/oembed.py`) is the one place external provider HTTP
  happens (ADR-0002). It uses `urllib.request` (no `requests` dependency) and
  tests patch `portfolio.oembed.urlopen` — the name *as imported into the
  module*, not `urllib.request.urlopen` — so endpoint construction and JSON
  parsing are exercised, not just an internal stub. `urllib` raises `HTTPError`
  (a `URLError` subclass) for non-2xx, so one `except URLError` cleanly covers
  both network-down and provider-4xx/5xx as `OEmbedError`.
- **Vimeo oembed real-world quirks (carried from the legacy stack, unverified
  against live here):** Vimeo's `thumbnail_url` comes back *extension-less* and
  404s unless `.jpg` is appended; Vimeo also gates oembed on a whitelisted
  `Referer` (`https://gracieanimator.squarespace.com`). YouTube/Speakerdeck need
  neither. Confirm these against live providers when the storyboard-save consumer
  wires `fetch()` in.
- **Speakerdeck 403s the default `Python-urllib` User-Agent.** Its oembed
  endpoint requires a browser-like `User-Agent`; Vimeo/YouTube don't care. A live
  integration test (`test_oembed_live.py`, opt-in via `-m live`) caught this —
  the mocked suite never would. The fix was a UA header on every oembed request.
  Live tests are deselected by default (`pytest.ini: -m "not live"`); a live
  failure often just means a fixture URL rotted, not a regression.

## Local test env (Slice 5)

- **The shell's `.envrc.local` leaks staging env into the test run.** It exports
  `DATABASE_URL` (remote RDS, no createdb perm → `pytest` dies with "permission
  denied to create database", `SystemExit: 2` on every DB test) and `R2_*`
  staging vars (→ `R2_ENABLED` True, failing `test_storage`). `config.settings`
  defaults to local `postgres:///gracie` only when `DATABASE_URL` is unset. Run
  the suite with those vars stripped:
  `env -u DATABASE_URL -u R2_BUCKET_NAME python -m pytest`. (`make test` assumes
  the plain direnv/Nix shell without the `.local` overrides.)

## Model abstraction (Slice 4)

- **imagekit `ImageSpecField`s are descriptors, not DB columns**, so they never
  appear in migrations. To DRY two structurally-identical types (Illustration /
  SketchbookSample per ADR-0003), extract a shared abstract base
  (`ImageProject(Project)`) holding the renditions (`gallery_image`,
  `thumbnail_rendition`) and `derived_thumbnail_url` — but **keep the `image`
  field on each concrete subclass** so each gets its own `upload_to` namespace.
  Moving only the spec fields up is migration-free for the existing type;
  unifying `image` onto the base with a callable `upload_to` would instead emit
  an `AlterField` rewriting the existing upload path. Verify with
  `makemigrations --dry-run` (expect only the new model's migration). The
  unchanged existing test suite is the guard that spec-field-on-abstract works.

## Storage / R2 (Slice 3)

- **Gate the media storage backend on `R2_BUCKET_NAME` presence, not `APP_ENV`.**
  Switching `STORAGES["default"]` to S3 unconditionally breaks every test and
  local dev: factories that save an `ImageField` would make a network call with
  no creds. Local FS stays the default; R2 turns on only when the bucket var is
  set. A prod guard (`APP_ENV=production` + no bucket → `ImproperlyConfigured`)
  prevents silently writing to Heroku's ephemeral disk.
- **imagekit renditions follow the `"default"` storage alias automatically**
  (`IMAGEKIT_DEFAULT_FILE_STORAGE` resolves to `DEFAULT_STORAGE_ALIAS` →
  `storages["default"]`). No extra imagekit config needed for renditions to land
  on R2.
- **R2 public serving gotcha:** the account endpoint
  (`<acct>.r2.cloudflarestorage.com`) only answers SigV4-*signed* requests.
  With `querystring_auth=False` and no custom domain, `url()` yields an unsigned
  URL that 401s on a public GET — so `<img src>` won't load. Public image
  serving REQUIRES `R2_CUSTOM_DOMAIN` (a mapped domain or `pub-*.r2.dev`) plus
  bucket public access enabled. The live AC #5 round-trip can't pass without it.
- **Testing import-time settings branches:** config/settings.py decides the
  storage backend at import time from env vars. Exercise the branches by
  importing `config.settings` in a clean subprocess with a controlled env
  (`portfolio/tests/test_storage.py`); a conftest fixture or `override_settings`
  runs too late to steer import-time decisions.
