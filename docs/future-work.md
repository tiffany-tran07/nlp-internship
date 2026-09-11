# Future Work Roadmap

## Near term

- Repair test fixtures and add coverage tooling so CI enforces the 70% line-coverage target.
- Normalize taxonomy aliases consistently across parser, extractor, and evaluation outputs.
- Add contract tests for every FastAPI route, including rate limiting, cache invalidation, and MySQL failure states.
- Pin or vendor the semantic model for reproducible offline evaluation.

## Medium term

- Replace token-overlap ranking with a hybrid BM25 plus embedding ranker and evaluate recall@k, MRR, and latency on a larger relevance set.
- Add schema versioning and data-quality checks for raw MLS exports.
- Add observability for latency percentiles, cache hit rate, parser confidence, and compliance-review volume.
- Add authentication, secret management, TLS termination, and production CORS policy.

## Longer term

- Introduce human feedback loops for query parsing and taxonomy expansion.
- Calibrate confidence thresholds and build an error-analysis dashboard.
- Add fair-housing policy review with domain experts and an auditable rule/version registry.
- Package the API and UI as separate deployable services with CI-built, vulnerability-scanned images.
