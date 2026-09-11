# Deployment Artifacts

## Container image

The repository contains the production `Dockerfile`. Build the image from the repository root:

```bash
docker build -t real-estate-nlp:local .
```

Run with the local corpus:

```bash
docker run --rm -p 8000:8000 \
  -e DB_AUTOLOAD=false \
  -e NLP_LISTINGS_PATH=/app/data/processed/listings.csv \
  -e NLP_TAXONOMY_PATH=/app/data/processed/taxonomy.json \
  real-estate-nlp:local
```

The image runs as non-root user `api` (UID 10001), exposes port 8000, and checks `/health` every 30 seconds.

## Compose stack

`docker-compose.yml` provisions MySQL 8.0 with database `real_estate`, root password `root`, a named data volume, and a read-only mount of `data/raw` into MySQL initialization. These credentials are development defaults only. For a shared environment, override them and provide secrets through the deployment system.

## Runtime configuration

Set `DB_AUTOLOAD=true` only when the MySQL service is reachable and contains the expected `rets_property` table. The API accepts `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_LISTING_LIMIT`, `NLP_CACHE_TTL_SECONDS`, `NLP_CACHE_MAX_ENTRIES`, `NLP_RATE_LIMIT_PER_SECOND`, `NLP_CORS_ORIGINS`, `NLP_LISTINGS_PATH`, and `NLP_TAXONOMY_PATH`.

No registry-published image is included in this workspace. The Dockerfile and compose configuration are the reproducible deployment artifacts; a CI pipeline should build, scan, tag, and publish the image.
