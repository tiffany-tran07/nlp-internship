import asyncio
import json
import os
import statistics
import time

os.environ["DB_AUTOLOAD"] = "false"

from fastapi import Response

from scripts.main import (
    ComplianceRequest,
    SearchRequest,
    SummarizeRequest,
    check_compliance,
    services,
    summarize,
)


def stats(samples):
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, int(len(ordered) * 0.95))
    return {
        "runs": len(ordered),
        "p50_ms": round(statistics.median(ordered), 2),
        "p95_ms": round(ordered[p95_index], 2),
    }


def measure_sync(fn, runs):
    fn()
    values = []
    for _ in range(runs):
        started = time.perf_counter()
        fn()
        values.append((time.perf_counter() - started) * 1000)
    return stats(values)


async def measure_async(fn, runs):
    await fn(0)
    values = []
    for index in range(runs):
        started = time.perf_counter()
        await fn(index + 1)
        values.append((time.perf_counter() - started) * 1000)
    return stats(values)


async def main():
    documents = [
        {
            "id": str(index),
            "text": "Irvine home with three bedrooms, two bathrooms, garage and pool"
            if index % 11 == 0
            else "California residential property listing with updated kitchen",
            "metadata": {
                "city": "Irvine" if index % 7 == 0 else "Anaheim",
                "price": 650000 if index % 13 == 0 else 850000,
                "bedrooms": 3,
                "bathrooms": 2,
            },
        }
        for index in range(52742)
    ]
    from scripts.main import Document

    services.replace_documents([Document(**item) for item in documents])
    query = "3 bed 2 bath under 700k in Irvine with a pool"
    filters, _ = services.parse(query)
    search_request = SearchRequest(query=query, top_k=10)

    report = {
        "method": "warm local component runtime; direct service path; Apple Silicon host",
        "search_corpus": len(documents),
        "search": measure_sync(lambda: services.search(search_request, filters), 15),
        "parse_query": measure_sync(lambda: services.parse(query), 100),
        "extract_entities": measure_sync(
            lambda: services.entities(
                "Updated 3 bedroom, 2 bathroom Irvine home with a pool, 1,850 square feet, listed at $695,000."
            ),
            100,
        ),
    }

    async def summarize_once(index):
        await summarize(
            SummarizeRequest(
                text=(
                    "Updated three bedroom home with a pool and solar panels. "
                    "The kitchen has quartz counters. The yard includes mature citrus trees. "
                    f"Benchmark sample {index}."
                ),
                max_sentences=2,
            ),
            Response(),
        )

    async def compliance_once(index):
        await check_compliance(
            ComplianceRequest(
                text=f"Ideal for families with children. Benchmark sample {index}.",
                text_type="listing",
            ),
            Response(),
        )

    report["summarize"] = await measure_async(summarize_once, 100)
    report["check_compliance"] = await measure_async(compliance_once, 100)
    print(json.dumps(report, indent=2))


asyncio.run(main())
