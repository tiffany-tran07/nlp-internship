# Test Coverage Report

## Verification snapshot

The checked-in Python 3.11 environment ran the focused core NLP suite on 11 September 2026. Result: **264 passed, 8 failed, 1 error** across 273 collected tests. A separate full-suite collection also fails before execution because the semantic-search model attempts a network download in the restricted environment.

The repository does not currently include `coverage.py` or `pytest-cov`, so a defensible line-coverage percentage could not be generated from the available environment. The 70%+ target remains a release gate, not a claim about the current state.

## Failure inventory

| Area | Result | Root cause |
| --- | --- | --- |
| Query parser aliases | 3 failures | Tests expect canonical aliases such as `3-car garage` and `solar`; parser returns surface forms |
| Price suffix extraction | 1 failure | `1.2m` is not normalized through the signal-extractor path |
| Taxonomy amenity coverage | 1 failure | Current taxonomy does not emit `quartz countertop` for the fixture |
| Numeric evaluation | 3 failures | Test expects `bedrooms`, `bathrooms`, and `sqft` columns while fixture uses `bed`, `bath`, and no `sqft` gold column |
| Answerability test | 1 collection error | `checker` fixture is referenced but not defined |
| Environment setup | collection failures | Semantic model and MySQL assumptions require local services/artifacts |

## Evaluation metrics already available

| Metric | Value | Sample |
| --- | ---: | ---: |
| Keyword precision@1 | 0.580 | 50 queries |
| Keyword MRR | 0.661 | 50 queries |
| Bedroom accuracy | 0.750 | 40 checks |
| Bathroom accuracy | 0.675 | 40 checks |
| Square-footage accuracy | 0.825 | 40 checks |
| Entity bedroom accuracy | 1.000 | 100 listings |
| Entity bathroom accuracy | 1.000 | 100 listings |
| Entity price accuracy | 0.880 | 100 listings |
| Taxonomy recall | 0.770 | 248 gold features |

## Path to the 70% gate

Add `coverage` and `pytest-cov` to the development requirements, add a `pytest.ini` configuration, repair the fixture/schema drift above, mock the semantic model and MySQL boundary, then run `pytest --cov=scripts --cov-report=term-missing --cov-fail-under=70`. Store the resulting HTML report under `deliverables/coverage-html/` in CI rather than committing generated caches.
