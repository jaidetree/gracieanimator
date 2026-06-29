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

## Mistakes to Avoid

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
  zero test edits (#25).
