# Cloudflare R2 media storage — setup guide

How to provision the staging and production R2 buckets and serve them over a
custom domain, then wire the result into this app's `R2_*` env vars.

Background: media uploads route to R2 via django-storages (ADR-0001). The app
turns R2 on when `R2_BUCKET_NAME` is set and serves public images from
`R2_CUSTOM_DOMAIN` — the account endpoint only answers signed requests, so a
public hostname is **required** for `<img src>` to load. See `LEARNINGS.md`.

Target domains:

- Production: `media.gracieanimator.lispcms.com`
- Staging: `media-staging.gracieanimator.lispcms.com`

## Why full setup, not partial (CNAME)

R2 custom domains require the domain to be a zone in your Cloudflare account.
Two ways to get there:

| | Partial (CNAME) setup | **Full setup** (chosen) |
|---|---|---|
| Plan | Business+ (~$200/mo) | Free |
| Nameservers | Stay at current provider | Move to Cloudflare |
| Other records | Stay where they are | Recreated in Cloudflare |

Partial is too expensive for this project. Full setup is free; it only means
Cloudflare hosts the DNS zone. Every existing record (including the fly.io
`A`/`AAAA` records for the main site) is recreated and kept **DNS only**
(grey-cloud) so traffic still goes straight to fly.io with Fly's own TLS. Only
the R2 media subdomains are proxied. See `## Step 1`.

---

## Step 1 — Move `lispcms.com` to Cloudflare (full setup)

One-time, for the whole zone. Skip if `lispcms.com` is already on Cloudflare.

1. Cloudflare dashboard → **Add a site** → enter `lispcms.com` → **Free** plan.
2. Cloudflare scans and imports existing DNS records. **Review the import
   carefully** — confirm every record came across, especially:
   - the fly.io `A`/`AAAA` (or `CNAME`) records for `gracieanimator` / the apex,
   - any `MX`, `TXT` (SPF/DKIM), and verification records.
   Add anything it missed.
3. Set the fly.io records to **DNS only (grey cloud)**. This keeps Fly
   terminating TLS and avoids Cloudflare-proxy-in-front-of-Fly issues
   (SSL-mode mismatch, `522`s).
4. At your registrar, replace the nameservers with the two Cloudflare ones
   shown in the dashboard.
5. Wait for the zone to go **Active** (minutes to a few hours). Verify the site
   still resolves to fly.io before continuing:

   ```sh
   dig +short gracieanimator.lispcms.com
   ```

End state on the zone:

```
gracieanimator         A/AAAA   <fly.io IPs>     DNS only  (grey)
media.gracieanimator   CNAME    <auto by R2>     Proxied   (orange)   # added in Step 4
```

## Step 2 — Create the buckets

R2 → **Create bucket**. Make two, one per environment, so staging uploads can
never touch production media:

- `gracie-media` (production)
- `gracie-media-staging` (staging)

Pick a location hint near your users; R2 is region-agnostic at the API
(`region_name="auto"`, already set in `config/settings.py`). Leave public
access **off** for now — the custom domain (Step 4) is what exposes objects,
not the bucket's `pub-*.r2.dev` URL.

Note the **account endpoint** shown in R2 settings — it is the same for both
buckets and per account:

```
https://<account-id>.r2.cloudflarestorage.com
```

This is `R2_ENDPOINT_URL`.

## Step 3 — Create API tokens (credentials)

R2 → **Manage R2 API Tokens** → **Create API token**.

- Permission: **Object Read & Write**.
- Scope: ideally one token per bucket (apply to a specific bucket) so a leaked
  staging token can't reach production. Create two tokens.
- TTL: leave as needed; rotate periodically.

On creation Cloudflare shows, once:

- **Access Key ID** → `R2_ACCESS_KEY_ID`
- **Secret Access Key** → `R2_SECRET_ACCESS_KEY`

Copy them straight into the secret store for that environment. They are not
recoverable later — regenerate if lost.

## Step 4 — Connect the custom domain per bucket

For each bucket: R2 → select bucket → **Settings** → **Custom Domains** →
**Add**.

1. Production bucket → enter `media.gracieanimator.lispcms.com`.
2. Staging bucket → enter `media-staging.gracieanimator.lispcms.com`.
3. Review the auto-generated `CNAME` (proxied) → **Connect Domain**.

Because the zone is on Cloudflare (Step 1), the DNS record is created
automatically — no manual entry. Status goes **Initializing → Active** within a
few minutes; refresh to confirm. Connecting a custom domain also makes those
objects publicly readable over that hostname (this is how R2 exposes a public
bucket without the `pub-*.r2.dev` URL).

Verify each is live:

```sh
curl -I https://media-staging.gracieanimator.lispcms.com/<some-key>
# expect HTTP/2 200 once an object exists at that key
```

These hostnames are `R2_CUSTOM_DOMAIN` (no scheme, no trailing slash — the
backend prepends `https://`).

## Step 5 — Wire up the app env vars

Set these per environment (staging app and production app). Names and behavior
are defined in `config/settings.py` / `.envrc.local.example`.

| Var | Staging | Production |
|---|---|---|
| `R2_BUCKET_NAME` | `gracie-media-staging` | `gracie-media` |
| `R2_ENDPOINT_URL` | `https://<account-id>.r2.cloudflarestorage.com` | same |
| `R2_ACCESS_KEY_ID` | staging token | prod token |
| `R2_SECRET_ACCESS_KEY` | staging token | prod token |
| `R2_CUSTOM_DOMAIN` | `media-staging.gracieanimator.lispcms.com` | `media.gracieanimator.lispcms.com` |

Reminders from `LEARNINGS.md`:

- Setting `R2_BUCKET_NAME` is what flips `STORAGES["default"]` from local disk to
  R2. Leave it unset locally to keep using the filesystem.
- `APP_ENV=production` with no bucket raises `ImproperlyConfigured` (guards
  against silently writing to ephemeral deploy disk).
- imagekit renditions follow the `default` storage alias automatically — no
  extra config; they land on R2 too.

## Step 6 — Verify the round-trip

In each deployed environment:

1. Upload an illustration through the admin/portfolio flow.
2. Confirm the object appears in the correct R2 bucket (Cloudflare dashboard).
3. Load the public page and confirm `<img>` renders — the URL should be
   `https://<R2_CUSTOM_DOMAIN>/...` and return `200`, not `401`.

A `401` on the image means the request is hitting the account endpoint instead
of the custom domain — recheck `R2_CUSTOM_DOMAIN` is set and the custom domain
shows **Active**.

## Optional hardening

- **Cache:** the proxied custom domain is cached at Cloudflare's edge for free.
  Default cache behavior is usually fine for immutable media; add a Cache Rule
  if you need longer TTLs.
- **CORS:** only needed if the browser fetches media via `fetch`/canvas rather
  than `<img>`. Add a bucket CORS policy then.
- **Hotlink / token auth:** not needed for a public portfolio. The bucket stays
  private at the API; only the custom domain is public.
