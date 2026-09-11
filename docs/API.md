# API Documentation

The service is a FastAPI application defined in `scripts/main.py`. Start it with `uvicorn scripts.main:app --host 0.0.0.0 --port 8000`. FastAPI also publishes the generated OpenAPI contract at `/openapi.json` and an interactive UI at `/docs`.

## Common behavior

Every request receives `X-Request-ID`, `X-RateLimit-Limit`, and `X-RateLimit-Remaining`. NLP responses also include `X-Cache: HIT` or `MISS`. The default limit is 10 requests per second per client IP. Rate-limited requests return HTTP 429 and `Retry-After`.

Errors use FastAPI's standard JSON shape, usually `{ "detail": "..." }`. Validation failures return HTTP 422.

## Endpoints

### `POST /search`

Request:

```json
{
  "query": "3 bed 2 bath under 700k in Irvine with a pool",
  "top_k": 10,
  "documents": null,
  "apply_query_filters": true
}
```

`documents` is optional. If omitted, the loaded corpus is searched. Each document must contain a non-empty `id`, `text`, and optional object `metadata`.

Response fields: `query`, `results`, `count`, and `parsed_filters`. Each result contains `id`, `text`, `score`, and `metadata`. Scores are token-overlap cosine-style scores rounded to six decimals.

### `POST /parse-query`

Request: `{ "query": "homes over 500k with garage", "include_sql": true }`.

Response contains `filters`; when `include_sql` is true it also contains `sql` and parameter values. SQL values are parameterized. The parser recognizes price bounds, bedroom/bathroom requirements, cities, amenities, exclusions, and free-text intent signals.

### `POST /extract-entities`

Request: `{ "text": "Updated 3 bedroom home with a pool priced at $650k" }`.

Response includes normalized text, numeric entities, amenity entities, and taxonomy-derived entity lists. With a configured taxonomy, the extractor returns canonical terms and aliases.

### `POST /summarize`

Request: `{ "text": "...", "max_sentences": 2, "max_characters": 1000 }`.

Response includes `summary`, `sentence_count`, and `original_characters`.

### `POST /check-compliance`

Request: `{ "text": "Family-friendly neighborhood", "text_type": "listing" }` where `text_type` is `listing` or `query`.

Response is produced by `ComplianceChecker` and contains the rule findings, severity, category, and review guidance.

### Corpus and operations

`PUT /documents` replaces the in-memory corpus and rejects duplicate document IDs. `POST /documents/reload` loads `rets_property` from MySQL and invalidates the cache. `GET /ready` exposes database status without failing liveness. `GET /cache/stats` reports entries, hits, misses, TTL, and capacity. `DELETE /cache` returns the number of removed entries.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `8000` | Container port |
| `NLP_LISTINGS_PATH` | unset | CSV path for parser/search data |
| `NLP_TAXONOMY_PATH` | unset | Taxonomy JSON path |
| `DB_AUTOLOAD` | `true` | Load MySQL at startup |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | localhost, 3306, root, empty, idx_exchange | MySQL connection |
| `NLP_CACHE_TTL_SECONDS` | 300 | Cache TTL |
| `NLP_CACHE_MAX_ENTRIES` | 1000 | Cache bound |
| `NLP_RATE_LIMIT_PER_SECOND` | 10 | Per-IP request limit |
| `NLP_CORS_ORIGINS` | empty | Comma-separated allowed origins |
