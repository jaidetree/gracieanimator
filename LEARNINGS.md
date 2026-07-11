# Project Learnings

Footguns and non-obvious facts for the Django migration. Prune when stale.

> **⚠️ Test env leak.** Local `.envrc.local` exports remote `DATABASE_URL`
> (no createdb perm → `pytest` dies "permission denied to create database") and
> `R2_*` (→ File/ImageField tests silently upload to the *real* bucket). Run
> storage/DB tests env-stripped: `env -u DATABASE_URL -u R2_BUCKET_NAME
> -u R2_ACCESS_KEY_ID -u R2_SECRET_ACCESS_KEY -u R2_ENDPOINT_URL
> -u R2_CUSTOM_DOMAIN pytest`. CI is inverse: needs an explicit TCP
> `DATABASE_URL` (base settings default to a unix socket the container rejects).

> **⚠️ Local Postgres won't start if another project's PG holds TCP 5432.**
> `scripts/db` doesn't set `listen_addresses`, so the project PG tries to bind
> TCP 5432 and `FATAL: could not create any TCP/IP sockets` → it shuts down
> even though Django only ever talks to the unix socket under `.pg/`. Don't kill
> the other project's DB — start this one socket-only:
> `pg_ctl start -D "$PWD/.pg/data" -l "$PWD/.pg/data/postgresql.log"
> -o "-c listen_addresses=''"`. A leftover `.pg/.s.PGSQL.5432` socket with no
> live postmaster is the stale-lock symptom.

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
- **Lock out the admin login with `django-axes`, keyed off the same client-IP
  seam as the gate** (#32). The admin login *is* a `contrib.auth` login (unlike
  the hand-rolled gate), so axes plugs straight in: `axes` in `INSTALLED_APPS`,
  `axes.backends.AxesStandaloneBackend` *first* in `AUTHENTICATION_BACKENDS`
  (it raises on a locked client before any real check, else returns None so
  `ModelBackend` after it authenticates), `axes.middleware.AxesMiddleware` after
  `AuthenticationMiddleware` (turns the raise into the friendly 429). No cache
  backend / `createcachetable` — axes counts in its **own DB tables** (ships
  migrations; the release-phase `migrate` provisions them). **`AXES_LOCKOUT_
  PARAMETERS = [["username", "ip_address"]]` — the *nested* list is an AND
  combination; a flat `["username", "ip_address"]` is OR, which makes one
  username lockable from anywhere = admin-account DoS.** Prove it both ways
  (same-IP/other-user and same-user/other-IP both stay open). `AXES_RESET_ON_
  SUCCESS` defaults to **False** — set `True` so a correct login clears the count.
  **ipware is *not* installed with axes 6.x**, so axes falls back to
  `REMOTE_ADDR` (the Heroku router → every admin locked behind one IP); point
  `AXES_CLIENT_IP_CALLABLE` at the shared **`config.client_ip.client_ip`** (last
  XFF hop) — the one seam #31's `client_ip_key` and #32's axes both delegate to,
  so the "which hop to trust" rule can't drift. Tests mirror #31: `AXES_ENABLED =
  False` in `config.test_settings`, opt back in per-test with `settings.AXES_
  ENABLED = True` + `AxesProxyHandler.reset_attempts()` (axes state is DB-backed →
  rolls back per test). Drive the real `POST /admin/login/` with distinct
  `HTTP_X_FORWARDED_FOR` IPs; the `admin_client` fixture's `force_login` bypasses
  axes (no auth signals) so existing admin suites are unaffected. Env-strip the
  run; pass `--create-db` the first time (axes adds migrations the reused DB lacks).

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
- **A new issue is *not* auto-added to project board #7**, and
  `gh project item-list 7` pages at **30 items** by default — a freshly-added
  issue lands past that page, so the `next(... number==N)` lookup StopIterations
  with an empty `ITEM_ID`. Fix: `gh project item-add 7 --owner jaidetree --url
  <issue-url>` first, then look up the item id with `--limit 100`.
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
  `preload=True` mismatch were written up as recommendations, not coded — see the
  security review, now a comment on issue #30 (was `docs/security-review.md`).
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
- **Branding is its own app** (`branding`, #35), not `contrib.sites` — the pool
  of per-visitor `Logo`s (name + `image` + validated `accent_color` hex +
  `is_active` gate). #35 ships only the owner-facing admin surface; random
  selection, session stickiness, a context processor, the `base.html` render,
  and the Tailwind `accent` utilities are later slices of Spec #34. Hex is
  guarded by a `RegexValidator` (`^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$`, no alpha)
  so the value can be emitted verbatim into `--color-accent`. `LogoAdmin` is the
  project's first `format_html` admin image preview (thumbnail + color swatch);
  `is_active` is `list_editable` to toggle the pool from the list.
- **Per-visitor branding is a context processor, mirroring `nav_pages` (#36).**
  `branding.context_processors.branding` reads `logo_id` from `request.session`;
  if absent *or* the id no longer resolves to an **active** logo, it picks a
  uniform-random active logo, writes the id back, and returns `{logo, accent_color}`.
  Store **only the id** — the `Logo` row stays source of truth (owner edits show
  instantly, no stale session data). Sticky per session for free via the existing
  `SESSION_EXPIRE_AT_BROWSER_CLOSE = True` (no config change). Stale/inactive/deleted
  ids are treated as unassigned → re-picked. `base.html`: `<head>` emits
  `<style>:root{--color-accent:{{ accent_color }}}</style>`; header renders the
  decorative `<img alt="">` (+ `sr-only <h1>` for the accessible name/SEO) or, on an
  empty pool, the visible text `<h1>` + default accent `#9E2820` and no `<img>`.
  Pick over a **materialized list of active `Logo` objects** so tests pin selection
  with `monkeypatch.setattr(random, "choice", lambda seq: seq[0])`. Test through the
  HTTP seam (`client.get("/")` + `client.session["logo_id"]`), not the processor.
- **`sr-only` (and any Tailwind util no template yet uses) isn't in the committed
  `stylesheet.css` until you `make css`.** JIT scans `templates/**/*.html`, so a
  class added to markup compiles only on the next build — rebuild and commit the CSS
  diff or the visually-hidden `<h1>` renders *visible* in prod.
- **A rendered `<img width height>` for CLS needs a real image in the factory.**
  `logo.image.width`/`.height` open the file, so `LogoFactory` uses
  `factory.django.ImageField(width=120, height=40, format="PNG")` (a valid PNG), not
  raw `SimpleUploadedFile(b"...")` bytes. The `Logo` model has no dimension fields
  (out of #36 scope) — dimensions are read from the image at render time.
