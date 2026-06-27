# Heroku hosting with Cloudflare R2 for media

The Django app and Postgres run on Heroku (git-push buildpack deploy). Because
Heroku's filesystem is ephemeral, all user-uploaded media (artwork, comic pages,
PDFs, fetched video posters) is stored in Cloudflare R2 via `django-storages`
(S3-compatible API), not on local disk.

## Considered Options

- **Local disk** — rejected: Heroku wipes the FS on every dyno restart/deploy.
- **AWS S3** — viable, but R2 has no egress fees, which matters for an
  image-heavy public portfolio.
- **Cloudinary** — image transforms built in, but vendor lock-in and tiered
  pricing; we generate our own renditions instead (see ADR-0003 thumbnails).

## Consequences

- Requires `django-storages` + `boto3`, R2 credentials in config, and
  `DEFAULT_FILE_STORAGE` pointed at the R2 bucket.
- Static assets (CSS/JS) are served separately by WhiteNoise; only *media*
  goes to R2.
- Cloudflare Pages/Workers cannot host the Django server itself — R2 is used
  for storage only.
