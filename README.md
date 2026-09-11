# Real Estate NLP Platform

Natural-language search and information extraction for real-estate listings. The platform combines a FastAPI REST API, a Streamlit search UI, deterministic NLP components, MySQL corpus loading, and fair-housing compliance checks.

## Quick start

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools
python -m pip install -r requirements.txt
```

Run the API with the local processed corpus:

```bash
export NLP_LISTINGS_PATH=data/processed/listings.csv
export NLP_TAXONOMY_PATH=data/processed/taxonomy.json
export DB_AUTOLOAD=false
uvicorn scripts.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for the interactive OpenAPI documentation. Run the UI in a second terminal:

```bash
source venv/bin/activate
NLP_API_URL=http://localhost:8000 streamlit run scripts/frontend/search.py
```

## Architecture overview

The Streamlit client sends JSON requests to FastAPI. `NLPServices` lazily loads the query parser, entity extractor, and compliance checker. Search uses token-overlap scoring in the production API and then applies structured filters. The service supports an in-memory bounded TTL cache, per-IP sliding-window rate limiting, structured request logs, document replacement, and optional MySQL startup loading. The API remains operational with conservative regex fallbacks when project data or optional NLP resources are unavailable.

```text
Streamlit UI -> FastAPI middleware -> NLPServices
                                      |-> query parser -> filters / SQL preview
                                      |-> entity extractor -> structured signals
                                      |-> summarizer
                                      |-> compliance checker
                                      |-> token search -> ranked listings
                                      |-> MySQL rets_property loader
```

## API surface

| Route | Purpose |
| --- | --- |
| `GET /health` | Liveness check |
| `GET /ready` | Readiness, database state, and loaded document count |
| `POST /search` | Parse a natural-language query and return ranked documents |
| `POST /parse-query` | Return structured filters and optional parameterized SQL |
| `POST /extract-entities` | Extract bedrooms, bathrooms, price, square feet, and taxonomy features |
| `POST /summarize` | Return a short listing summary |
| `POST /check-compliance` | Check listing or query text for fair-housing issues |
| `PUT /documents` | Replace the in-memory corpus |
| `POST /documents/reload` | Reload the corpus from MySQL |
| `GET /cache/stats` / `DELETE /cache` | Inspect or clear the cache |

Detailed request and response schemas live in [docs/API.md](docs/API.md) and [docs/data-schema.md](docs/data-schema.md).

## Docker deployment

Build and run the API image:

```bash
docker build -t real-estate-nlp:local .
docker run --rm -p 8000:8000 \
  -e DB_AUTOLOAD=false \
  -e NLP_LISTINGS_PATH=/app/data/processed/listings.csv \
  -e NLP_TAXONOMY_PATH=/app/data/processed/taxonomy.json \
  real-estate-nlp:local
```

`docker-compose.yml` starts MySQL 8.0 and mounts `data/raw` as initialization input. Configure the API database variables before enabling `DB_AUTOLOAD=true`.

## Evaluation and known limitations

The committed evaluation files contain 50 search queries, 40 structured-field checks, 100 entity examples, and 100 taxonomy examples. The current offline evaluation reports keyword MRR 0.661, keyword precision@1 0.580, bedroom accuracy 0.750, bathroom accuracy 0.675, square-footage accuracy 0.825, and taxonomy recall 0.770.

The test suite currently has dependency/data drift that must be resolved before claiming a 70%+ line-coverage gate: the semantic search tests need the local Hugging Face model, the setup test expects a different dependency environment, the taxonomy fixture expects a legacy `terms` key, and several tests use stale column names. See [docs/coverage-report.md](docs/coverage-report.md) for the exact verification snapshot.

## Project materials

- [Technical API documentation](docs/API.md)
- [Data schemas](docs/data-schema.md)
- [Coverage and test report](docs/coverage-report.md)
- [Demo recording script](docs/demo-video-script.md)
- [Future work roadmap](docs/future-work.md)
- [Written project report](deliverables/real_estate_nlp_project_report.docx)
- [Presentation](deliverables/real_estate_nlp_project_final_presentation.pptx)
