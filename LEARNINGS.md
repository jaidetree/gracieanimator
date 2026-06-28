# Learnings

Session memory for the Django migration. Newest first. Prune when stale.

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
