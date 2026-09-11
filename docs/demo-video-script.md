# Demo Video Script

The repository contains a presentation and this recording-ready script. A binary screen recording is not included because the workspace has no recording or publishing target configured.

Target length: 3 to 4 minutes.

1. Show the architecture slide. Explain that Streamlit sends natural-language requests to FastAPI, which routes to parsing, extraction, search, summarization, and compliance services.
2. Open `/docs` and call `GET /health` and `GET /ready`. Point out the request ID, rate-limit headers, and database/document status.
3. Call `POST /parse-query` with `3 bed 2 bath under 700k in Irvine with a pool`. Show the structured price, bedroom, bathroom, city, and amenity filters.
4. Call `POST /search` with the same query. Show ranked listing IDs, relevance scores, and metadata. Repeat the request to show the cache changing from `MISS` to `HIT`.
5. Call `POST /extract-entities` on a listing remark containing price, bedrooms, square feet, and amenities. Explain canonical taxonomy terms.
6. Call `POST /check-compliance` on a listing phrase that requires review. Show that the result is a review signal rather than an automatic decision.
7. Close with the evaluation slide: keyword MRR 0.661, entity bedroom and bathroom accuracy 1.000, and taxonomy recall 0.770. State that the coverage gate remains pending until the documented test drift is repaired.
