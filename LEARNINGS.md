# Project Learnings

Footguns and non-obvious facts for the Django migration. Prune when stale.

> **⚠️ Test env leak.** Local `.envrc.local` exports remote `DATABASE_URL`
> (no createdb perm → `pytest` dies "permission denied to create database") and
> `R2_*` (→ File/ImageField tests silently upload to the *real* bucket). Run
> storage/DB tests env-stripped: `env -u DATABASE_URL -u R2_BUCKET_NAME
> -u R2_ACCESS_KEY_ID -u R2_SECRET_ACCESS_KEY -u R2_ENDPOINT_URL
> -u R2_CUSTOM_DOMAIN pytest`. CI is inverse: needs an explicit TCP
> `DATABASE_URL` (base settings default to a unix socket the container rejects).

## Patterns That Work

- **Test the effect through the real seam, not config.** Drive the bound formset
  / the actual storage backend (`get_django_storage().exists()`, not a parallel
  `tmp_path`) / the session cookie — never `settings.X is True`.
- **One boundary per external concern, mocked at the imported name** (patch
  `portfolio.oembed.urlopen`, not `urllib...`). oembed HTTP, media storage, the
  HTML sanitizer each have a single seam tests target.
- **Add featured content via the `FEATURED_TYPES` registry** — ordered
  `(model, label, reverse_lazy(url))`; `featured_projects()` skips empties.
- **One breadcrumb seam: `_breadcrumb.html` + a `breadcrumbs` context list**
  of `(label, url)` ancestor crumbs (#26). The current page's title stays in
  the `<h1>` and is never a crumb, so "which crumbs" is mechanical per view.
  Labels are lowercased in the partial (the one place that rule lives), so
  views pass natural-case labels — including DB category names — and every
  trail reads "portfolio / comics /". Home and static Pages pass no list →
  the partial renders nothing. Tests read the trail back by regexing the
  `aria-label="Breadcrumb"` nav, not the whole page.
- **Make unsaved inline rows sortable by *promoting* them into sortable2's
  existing Sortable, not a second one** (#27). sortable2 only drives
  `tr.has_original` (the grip is drawn on `td.original p`; `onEnd` rewrites the
  `input._reorder_` of every `tr.has_original` on drop). A row added via "Add
  another" has neither, so it's undraggable until saved. `inline_sortable_new.js`
  listens for Django's bubbling `formset:added` and, for a new row inside a
  `fieldset.sortable`, adds `has_original` + an empty handle `<p>`. SortableJS
  evaluates `draggable`/`handle`/`onMove` at pointer time and re-queries
  `tr.has_original` on drop, so a row promoted *after* init joins fully — no
  competing Sortable on the tbody. Test the promotion (row gains the class +
  handle + `_reorder_` input), not a simulated drop — SortableJS-drag-under-
  Playwright is flaky and the drop engine is already trusted for saved rows.
- **Rate-limit a custom view with `django-ratelimit`, tested through the real DB
  cache** (#31). The storyboard gate is a hand-rolled view, not a `contrib.auth`
  login, so `@ratelimit(key=..., rate="5/m", method="POST", block=False)` fits
  (axes would fight it). `block=False` sets `request.limited` instead of raising,
  so the over-limit branch stays *in the view* — render the friendly form at
  status 429 before the password check, so a blocked request fails closed.
  Counting needs a **shared** cache (DB cache; the default LocMemCache is per-dyno
  and resets on restart), keyed on the *last* `X-Forwarded-For` hop — behind
  Heroku's router `REMOTE_ADDR` is the router and the first XFF entry is
  client-spoofable. Provision the DB cache table with `createcachetable` (a
  command, *not* a migration) in the Procfile `release:` phase + once locally.
  Tests: set `RATELIMIT_ENABLE = False` in `config.test_settings` so the #30
  many-POST gate suites don't trip the limiter, then opt back in *per test* with
  `settings.RATELIMIT_ENABLE = True`. Drive the real seam: `call_command(
  "createcachetable")` inside the test (PG DDL is transactional → the table lives
  for the rolled-back transaction, no global state to clean up), `cache.clear()`,
  give each test a distinct documentation-range IP via `HTTP_X_FORWARDED_FOR`,
  and assert the *transition* (`statuses[0]==200`, `statuses[-1]==429`) not an
  exact boundary index. Env-strip the run (it touches the database).

## Mistakes to Avoid

- **`manage.py check --deploy` false-positives in dev/test** because the prod
  hardening (SSL/HSTS/secure cookies) is gated on `if IS_PROD:`. Audit the real
  thing under a prod-like env that clears the boot guards: `env -u DATABASE_URL …
  APP_ENV=production SECRET_KEY=$(python -c 'import
  secrets;print(secrets.token_urlsafe(50))') ALLOWED_HOSTS=… R2_BUCKET_NAME=…
  R2_ENDPOINT_URL=… R2_ACCESS_KEY_ID=… R2_SECRET_ACCESS_KEY=… python manage.py
  check --deploy`. A short dummy `SECRET_KEY` trips W009 — use a 50-char one. It
  came back fully clean, so the prod settings block is the trusted baseline (#30).
- **A GET that only renders a form persists no session**, so there's no
  `sessionid` cookie to read back. To test session-key cycling, seed + `save()`
  `client.session`, capture `.session_key`, POST, then assert the new
  `client.session.session_key` differs (#30).
- **`ImageField` silently rejects non-images** (Pillow). Use `FileField` for
  PDFs/other files.
- **`override_settings` breaks in two places:** in a `pytestmark` list it dies at
  collection (use the pytest-django `settings` fixture); it never reaches the
  `live_server` thread (bake E2E defaults into `config.test_settings`).
- **`nh3.clean` owns `a@rel`** — listing `"rel"` in `a` attrs raises `ValueError`.
- **CKEditor emits `<p>&nbsp;</p>` for a blank doc** → `{% if body %}` truthy →
  phantom nav. `sanitize_html` must collapse visually-empty HTML to `""`.
- **An always-present `extra` inline row blocks the save** (setting a field on it
  flips `has_changed()` → full validation → "required"). Use `extra = 0`.
- **`get_fields(req, obj)` on an admin with an FK to a *registered* admin builds
  the real form** → needs `request.user`; a bare `RequestFactory().get()` blows up.
- **Don't let `ruff --fix`/`format` rewrite unseen** — `--check` first. Keep
  `ignore=["E501"]` (the formatter won't fix it on comments/strings).
- **Test import-time settings branches in a subprocess** — fixtures /
  `override_settings` run too late.
- **Asserting a rendition URL opens the source image; asserting the field URL
  doesn't.** `sb.thumbnail.url` is a cheap string, but `sb.thumbnail_rendition.url`
  makes imagekit open the source → a fake upload (`b"img-bytes"`) raises
  `UnidentifiedImageError`. Seed a real JPEG (`Image.new(...).save(buf, "JPEG")`)
  whenever a test reads through a rendition.
- **`--reuse-db` can carry a polluted local `test_gracie` across runs.** Symptoms:
  order-accumulation in admin tests (e.g. 7 Illustration rows when 3 were created,
  `order` 5/6 instead of 1/2) and imagekit `FileNotFoundError` / `ImageCacheFile
  not subscriptable` when a rendition's source file lived in a since-deleted temp
  `MEDIA_ROOT`. Leftover *committed* rows (an interrupted transactional/E2E run)
  reference gone files. CI is green because it builds a fresh DB. Fix:
  `./scripts/test.sh --create-db` once, then normal runs stay green — it is not a
  code bug.

## Domain Knowledge

- **`django-admin-sortable2` fully owns the sort field:** omit it from
  `list_display` (handle → left) and `list_editable`; it strips the field from
  `get_fields` (re-add for `obj is not None` to keep a typeable input) and forces
  inlines to drag-only `HiddenInput`; new rows auto-number. Use
  `SortableTabularInline`; parent needs `SortableAdminMixin`. Reorder endpoint:
  `admin:<app>_<model>_sortable_update`, POST `{"updatedItems": [[pk, order]]}`.
- **`static/css/stylesheet.css` is a committed Tailwind build artifact** — new
  template utility classes produce an unstaged diff there; commit it *with* the
  templates or styles won't apply in prod.
- **These emit no migration:** imagekit `ImageSpecField`s (descriptors), model
  field reorders. **These do:** `help_text`-only edits. Run `makemigrations
  --check` and expect only the delta you intend.
- **Model field declaration order drives the auto-built admin form order.**
- **Media storage gates on `R2_BUCKET_NAME` presence, not `APP_ENV`.** R2 public
  serving needs `R2_CUSTOM_DOMAIN` (account endpoint only answers SigV4 → bare
  `url()` 401s on public GET).
- **CKEditor `mediaEmbed.previewsInData: True`** stores a renderable `<iframe>`
  (default stores a non-rendering `<oembed url>`). Extend the nh3 allowlist (keep
  `iframe`, `figure`, `data-oembed-url`) — don't replace it.
- **oembed quirks** (confirm live, `-m live`): Vimeo `thumbnail_url` needs `.jpg`
  appended and a whitelisted `Referer`; Speakerdeck 403s the `Python-urllib` UA.
  A live failure usually means a fixture URL rotted.
- **Multi-image project = parent `Project` + child rows** (`ComicPage` FK +
  `order`), not an array field. Storyboard has no `image` field — thumbnail falls
  back to the first video's oembed `poster_url`.
- **Autouse `stub_oembed` (conftest) keeps factory media off the network**;
  `test_oembed*` modules opt out to hit the real `urlopen` seam.
- **One thumbnail seam: `Project.thumbnail_url`** (+ `_thumbnail.html` partial,
  the only place the img-or-nothing `{% if %}` lives). The base owns the
  manual-wins rule; each type supplies two hooks — `_manual_thumbnail_url` (how a
  manual upload renders) and `_derived_thumbnail_url` (the fallback). The per-type
  behaviour is irreducible: Storyboard renditions its *manual* upload (grids never
  need the full image) while Illustration/Sketchbook/Comic serve theirs full;
  derivation is image-rendition / cover-page `grid_image` / first-video poster.
  Don't try to unify into one body or a dispatch module — there's no public
  `derived_thumbnail_url`/`grid_thumbnail_url` anymore (#22, #23).
- **The Storyboard password gate lives in `portfolio/storyboard_gate.py`** (not
  `views.py`): the `SESSION_AUTH_KEY` string, `storyboards_required`, and the
  login/logout views. `views.py` imports only the decorator; `config/urls.py`
  routes `/auth/` + `/logout/` at the gate module directly. The gate tests
  (`test_storyboard_gate`, `_e2e`) drive the HTTP seam, so the extraction needed
  zero test edits (#25). It's the only hand-rolled auth path, so it's where the
  security review hardened: `constant_time_compare` for the password,
  `request.session.cycle_key()` on unlock (session fixation), and `or ""` so a
  fieldless POST fails closed. Brute-force/rate-limiting and the HSTS max-age vs
  `preload=True` mismatch were written up as recommendations, not coded —
  see `docs/security-review.md` (#30).
- **An inline's formset prefix is its FK `related_name`, not `<model>_set`.**
  `ComicPage`'s FK to `Comic` is `related_name="pages"`, so the admin inline DOM
  uses that prefix everywhere: group `#pages-group`, added rows
  `tr.dynamic-pages` (ids `pages-0`…), empty template `#pages-empty`, management
  inputs `id_pages-TOTAL_FORMS`. Admin DOM / Playwright selectors must key off
  the related_name.
- **An `InlineModelAdmin` `class Media` *does* load its JS.** Django's
  `MediaDefiningClass` gives every subclass a `media` property that combines the
  inherited core media with the class's `Media`, and `InlineAdminFormSet.media`
  includes `self.opts.media`. So a shared base inline with `class Media` is a
  valid way to ship admin JS to several inlines (#27).
