"""Production REST API for the real-estate NLP services.

Run with: uvicorn scripts.main:app --host 0.0.0.0 --port 8000

Set NLP_LISTINGS_PATH and NLP_TAXONOMY_PATH to use project data. Without
them, conservative regex fallbacks keep every endpoint operational.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import math
import os
import re
import threading
import time
import uuid
from collections import Counter, OrderedDict, defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool


@dataclass(frozen=True)
class Settings:
    cache_ttl_seconds: int = int(os.getenv("NLP_CACHE_TTL_SECONDS", "300"))
    cache_max_entries: int = int(os.getenv("NLP_CACHE_MAX_ENTRIES", "1000"))
    rate_limit_per_second: int = int(os.getenv("NLP_RATE_LIMIT_PER_SECOND", "10"))
    listings_path: str | None = os.getenv("NLP_LISTINGS_PATH")
    taxonomy_path: str | None = os.getenv("NLP_TAXONOMY_PATH")
    db_autoload: bool = os.getenv("DB_AUTOLOAD", "true").lower() in {"1", "true", "yes", "on"}
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "3306"))
    db_user: str = os.getenv("DB_USER", "root")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_name: str = os.getenv("DB_NAME", "idx_exchange")
    db_connect_timeout_seconds: int = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "5"))
    db_listing_limit: int = max(0, int(os.getenv("DB_LISTING_LIMIT", "0")))
    cors_origins: tuple[str, ...] = tuple(
        item.strip() for item in os.getenv("NLP_CORS_ORIGINS", "").split(",") if item.strip()
    )


settings = Settings()
logging.basicConfig(level=os.getenv("NLP_LOG_LEVEL", "INFO").upper(), format="%(message)s")
logger = logging.getLogger("nlp_api")


def log_event(event: str, **values: Any) -> None:
    logger.info(json.dumps({"event": event, **values}, default=str, sort_keys=True))


class Document(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=100_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=10, ge=1, le=100)
    documents: list[Document] | None = Field(default=None, max_length=10_000)
    apply_query_filters: bool = True


class SearchResult(BaseModel):
    id: str
    text: str
    score: float
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    count: int
    parsed_filters: dict[str, Any]


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)


class ParseQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    include_sql: bool = False


class SummarizeRequest(TextRequest):
    max_sentences: int = Field(default=2, ge=1, le=10)
    max_characters: int = Field(default=1_000, ge=50, le=10_000)


class ComplianceRequest(TextRequest):
    text_type: Literal["listing", "query"] = "listing"


class DocumentsRequest(BaseModel):
    documents: list[Document] = Field(max_length=50_000)


class TTLCache:
    """Thread-safe bounded in-memory TTL cache."""

    def __init__(self, ttl_seconds: int, max_entries: int):
        self.ttl_seconds = max(1, ttl_seconds)
        self.max_entries = max(1, max_entries)
        self._values: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any | None:
        now = time.monotonic()
        with self._lock:
            item = self._values.get(key)
            if item is None:
                self.misses += 1
                return None
            expires_at, value = item
            if expires_at <= now:
                del self._values[key]
                self.misses += 1
                return None
            self._values.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._values[key] = (time.monotonic() + self.ttl_seconds, value)
            self._values.move_to_end(key)
            while len(self._values) > self.max_entries:
                self._values.popitem(last=False)

    def clear(self) -> int:
        with self._lock:
            count = len(self._values)
            self._values.clear()
            return count

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "entries": len(self._values), "hits": self.hits, "misses": self.misses,
                "max_entries": self.max_entries, "ttl_seconds": self.ttl_seconds,
            }


class SlidingWindowRateLimiter:
    def __init__(self, requests_per_second: int):
        self.limit = max(1, requests_per_second)
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, client_id: str) -> tuple[bool, int, float]:
        now = time.monotonic()
        with self._lock:
            window = self._requests[client_id]
            while window and window[0] <= now - 1.0:
                window.popleft()
            if len(window) >= self.limit:
                return False, 0, max(0.01, 1.0 - (now - window[0]))
            window.append(now)
            return True, self.limit - len(window), 0.0


cache = TTLCache(settings.cache_ttl_seconds, settings.cache_max_entries)
limiter = SlidingWindowRateLimiter(settings.rate_limit_per_second)


def model_data(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")  # type: ignore[attr-defined]
    return model.dict()


def cache_key(operation: str, payload: BaseModel) -> str:
    encoded = json.dumps(model_data(payload), sort_keys=True, separators=(",", ":"), default=str)
    return f"{operation}:{hashlib.sha256(encoded.encode()).hexdigest()}"


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")


class NLPServices:
    """Lazy facade over the existing NLP modules with safe fallbacks."""

    def __init__(self) -> None:
        self._parser: Any | None = None
        self._extractor: Any | None = None
        self._checker: Any | None = None
        self._load_attempted: set[str] = set()
        self._documents: list[dict[str, Any]] = []
        self._documents_version = 0
        self._database_state: dict[str, Any] = {
            "status": "not_loaded",
            "documents_loaded": 0,
            "loaded_at": None,
            "error": None,
        }
        self._lock = threading.RLock()

    def _load_parser(self) -> Any | None:
        if "parser" not in self._load_attempted:
            self._load_attempted.add("parser")
            try:
                from scripts.query_parser import QueryParser

                kwargs: dict[str, Any] = {}
                if settings.listings_path:
                    kwargs["listings_path"] = settings.listings_path
                else:
                    with self._lock:
                        kwargs["valid_cities"] = sorted(
                            {
                                str(document.get("metadata", {}).get("city", "")).strip()
                                for document in self._documents
                                if str(document.get("metadata", {}).get("city", "")).strip()
                            }
                        )
                if settings.taxonomy_path:
                    kwargs["taxonomy_path"] = settings.taxonomy_path
                else:
                    kwargs["valid_amenities"] = [
                        "pool",
                        "garage",
                        "solar panels",
                        "air conditioning",
                        "fireplace",
                        "home office",
                    ]
                self._parser = QueryParser(**kwargs)
            except Exception as exc:
                log_event("service_fallback", service="query_parser", error=str(exc))
        return self._parser

    def _load_extractor(self) -> Any | None:
        if "extractor" not in self._load_attempted:
            self._load_attempted.add("extractor")
            if settings.taxonomy_path:
                try:
                    from scripts.entity_extractor import EntityExtractor
                    self._extractor = EntityExtractor(settings.taxonomy_path)
                except Exception as exc:
                    log_event("service_fallback", service="entity_extractor", error=str(exc))
        return self._extractor

    def _load_checker(self) -> Any:
        if "checker" not in self._load_attempted:
            self._load_attempted.add("checker")
            from scripts.compliance_checker import ComplianceChecker
            self._checker = ComplianceChecker()
        return self._checker

    @staticmethod
    def _fallback_parse(query: str) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        lowered = " ".join(query.lower().split())

        def number(raw: str, suffix: str = "") -> int | float:
            value = float(raw.replace(",", "")) * {"k": 1_000, "m": 1_000_000}.get(suffix, 1)
            return int(value) if value.is_integer() else value

        match = re.search(r"\b(?:under|below|up to|no more than|max(?:imum)?)\s*\$?([\d,.]+)\s*([km])?\b", lowered)
        if match:
            filters["price_max"] = number(match.group(1), match.group(2) or "")
        match = re.search(r"\b(?:over|above|at least|min(?:imum)?)\s*\$?([\d,.]+)\s*([km])\b", lowered)
        if match:
            filters["price_min"] = number(match.group(1), match.group(2))
        beds = re.search(r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:bed|beds|bedroom|bedrooms|br)\b", lowered)
        baths = re.search(r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:bath|baths|bathroom|bathrooms|ba)\b", lowered)
        if beds:
            filters["bedrooms_min" if "+" in beds.group(0) else "bedrooms"] = float(beds.group(1))
        if baths:
            filters["bathrooms_min" if "+" in baths.group(0) else "bathrooms"] = float(baths.group(1))
        amenities = [item for item in ("pool", "garage", "solar panels", "air conditioning", "fireplace", "home office") if re.search(rf"\b{re.escape(item)}\b", lowered)]
        if amenities:
            filters["amenities"] = amenities
        return filters

    def parse(self, query: str) -> tuple[dict[str, Any], tuple[str, list[Any]] | None]:
        parser = self._load_parser()
        if parser is None:
            return self._fallback_parse(query), None
        filters = parser.parse(query)
        return filters, parser.to_sql(filters)

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"https?://\S+|www\.\S+", " url ", text, flags=re.I)
        return " ".join(text.lower().split())

    def entities(self, text: str) -> dict[str, Any]:
        cleaned = self._clean_text(text)
        extractor = self._load_extractor()
        if extractor is not None:
            result = extractor.extract_all(raw_text=text, cleaned_text=cleaned)
            result["cleaned_text"] = cleaned
            return result

        def first(pattern: str) -> float | None:
            match = re.search(pattern, cleaned, re.I)
            return float(match.group(1).replace(",", "")) if match else None

        match = re.search(r"\$\s*([\d,]+(?:\.\d+)?)\s*([km])?", text, re.I)
        price: int | float | None = None
        if match:
            price = float(match.group(1).replace(",", "")) * {"k": 1_000, "m": 1_000_000}.get((match.group(2) or "").lower(), 1)
            price = int(price) if price.is_integer() else price
        amenities = [item for item in ("pool", "garage", "solar panels", "air conditioning", "fireplace", "home office") if re.search(rf"\b{re.escape(item)}\b", cleaned)]
        return {
            "bedrooms": first(r"\b(\d+(?:\.\d+)?)\s*(?:bed|beds|bedroom|bedrooms|br)\b"),
            "bathrooms": first(r"\b(\d+(?:\.\d+)?)\s*(?:bath|baths|bathroom|bathrooms|ba)\b"),
            "price": price,
            "sqft": first(r"\b([\d,]{3,9})\s*(?:sq\.?\s*ft\.?|square feet|sf)\b"),
            "amenities": amenities, "entities": {"amenities": amenities}, "cleaned_text": cleaned,
        }

    def compliance(self, text: str, text_type: str) -> dict[str, Any]:
        return self._load_checker().check(text, text_type)

    def load_documents_from_database(self) -> dict[str, Any]:
        """Load searchable listings from MySQL and atomically replace the corpus."""
        with self._lock:
            self._database_state = {
                **self._database_state,
                "status": "loading",
                "error": None,
            }

        connection = None
        cursor = None
        try:
            import mysql.connector

            connection = mysql.connector.connect(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name,
                connection_timeout=max(1, settings.db_connect_timeout_seconds),
            )
            cursor = connection.cursor(dictionary=True)
            query = """
                SELECT
                    L_ListingID AS listing_id,
                    L_Address AS address,
                    L_City AS city,
                    L_Keyword2 AS bedrooms,
                    LM_Dec_3 AS bathrooms,
                    L_SystemPrice AS price,
                    L_Remarks AS remarks
                FROM rets_property
                WHERE L_Remarks IS NOT NULL
                  AND LENGTH(TRIM(L_Remarks)) > 50
                ORDER BY L_ListingID
            """
            if settings.db_listing_limit:
                # The value is parsed as a non-negative integer at startup, so
                # interpolation here cannot introduce arbitrary SQL.
                query += f" LIMIT {settings.db_listing_limit}"
            cursor.execute(query)

            documents_by_id: dict[str, Document] = {}
            for row in cursor:
                listing_id = row.get("listing_id")
                remarks = row.get("remarks")
                if listing_id is None or not isinstance(remarks, str) or not remarks.strip():
                    continue
                document_id = str(listing_id)
                documents_by_id[document_id] = Document(
                    id=document_id,
                    text=remarks.strip(),
                    metadata={
                        "address": row.get("address"),
                        "city": row.get("city"),
                        "bedrooms": row.get("bedrooms"),
                        "bathrooms": row.get("bathrooms"),
                        "price": row.get("price"),
                    },
                )

            count = self.replace_documents(list(documents_by_id.values()))
            # Recreate the parser on its next use so its city vocabulary is
            # derived from the newly loaded database corpus.
            with self._lock:
                self._parser = None
                self._load_attempted.discard("parser")
            cache.clear()
            state = {
                "status": "connected",
                "documents_loaded": count,
                "loaded_at": datetime.now(timezone.utc).isoformat(),
                "error": None,
            }
            with self._lock:
                self._database_state = state
            log_event(
                "database_documents_loaded",
                host=settings.db_host,
                database=settings.db_name,
                documents=count,
            )
        except Exception as exc:
            state = {
                "status": "error",
                "documents_loaded": self.document_count,
                "loaded_at": self._database_state.get("loaded_at"),
                "error": str(exc),
            }
            with self._lock:
                self._database_state = state
            log_event(
                "database_load_failed",
                host=settings.db_host,
                database=settings.db_name,
                error=str(exc),
            )
        finally:
            if cursor is not None:
                cursor.close()
            if connection is not None and connection.is_connected():
                connection.close()

        return dict(state)

    def load_documents_from_file(self, listings_path: str) -> dict[str, Any]:
        """Load the configured local listings CSV into the search corpus."""
        try:
            with open(listings_path, "r", encoding="utf-8-sig", newline="") as handle:
                rows = csv.DictReader(handle)
                documents_by_id: dict[str, Document] = {}
                for row in rows:
                    listing_id = next(
                        (row.get(name) for name in ("listing_id", "id", "L_ListingID") if row.get(name)),
                        None,
                    )
                    text = next(
                        (row.get(name) for name in ("remarks", "text", "L_Remarks") if row.get(name)),
                        None,
                    )
                    if not listing_id or not text or not text.strip():
                        continue

                    documents_by_id[str(listing_id)] = Document(
                        id=str(listing_id),
                        text=text.strip(),
                        metadata={
                            "address": row.get("address") or row.get("L_Address"),
                            "city": row.get("city") or row.get("L_City"),
                            "bedrooms": row.get("bedrooms") or row.get("bed") or row.get("L_Keyword2"),
                            "bathrooms": row.get("bathrooms") or row.get("bath") or row.get("LM_Dec_3"),
                            "price": row.get("price") or row.get("L_SystemPrice"),
                        },
                    )

            count = self.replace_documents(list(documents_by_id.values()))
            state = {
                "status": "local",
                "documents_loaded": count,
                "loaded_at": datetime.now(timezone.utc).isoformat(),
                "error": None,
            }
            with self._lock:
                self._database_state = state
            cache.clear()
            log_event("file_documents_loaded", path=listings_path, documents=count)
        except Exception as exc:
            state = {
                "status": "error",
                "documents_loaded": self.document_count,
                "loaded_at": self._database_state.get("loaded_at"),
                "error": str(exc),
            }
            with self._lock:
                self._database_state = state
            log_event("file_load_failed", path=listings_path, error=str(exc))

        return dict(state)

    def replace_documents(self, documents: list[Document]) -> int:
        values = [model_data(document) for document in documents]
        ids = [value["id"] for value in values]
        if len(ids) != len(set(ids)):
            raise ValueError("Document ids must be unique.")
        with self._lock:
            self._documents = values
            self._documents_version += 1
        return len(values)

    @property
    def document_count(self) -> int:
        with self._lock:
            return len(self._documents)

    @property
    def database_state(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._database_state)

    @property
    def documents_version(self) -> int:
        with self._lock:
            return self._documents_version

    def search(self, request: SearchRequest, filters: dict[str, Any]) -> list[dict[str, Any]]:
        documents = [model_data(item) for item in request.documents] if request.documents is not None else self._documents
        query_counts = Counter(TOKEN_PATTERN.findall(request.query.lower()))
        query_norm = math.sqrt(sum(value * value for value in query_counts.values())) or 1.0
        results: list[dict[str, Any]] = []
        for document in documents:
            metadata = document.get("metadata", {})
            if request.apply_query_filters and not self._matches_filters(metadata, filters):
                continue
            doc_counts = Counter(TOKEN_PATTERN.findall(document["text"].lower()))
            overlap = sum(min(count, doc_counts[token]) for token, count in query_counts.items())
            doc_norm = math.sqrt(sum(value * value for value in doc_counts.values())) or 1.0
            score = overlap / (query_norm * doc_norm)
            if score > 0:
                results.append({**document, "score": round(score, 6)})
        results.sort(key=lambda item: (-item["score"], item["id"]))
        return results[:request.top_k]

    @staticmethod
    def _matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
        aliases = {"price": ("price", "L_SystemPrice"), "bedrooms": ("bedrooms", "beds", "L_Keyword2"), "bathrooms": ("bathrooms", "baths", "LM_Dec_3")}
        for field, names in aliases.items():
            raw = next((metadata[name] for name in names if name in metadata), None)
            if raw is None:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if filters.get(field) is not None and value != float(filters[field]):
                return False
            if filters.get(f"{field}_min") is not None and value < float(filters[f"{field}_min"]):
                return False
            if filters.get(f"{field}_max") is not None and value > float(filters[f"{field}_max"]):
                return False
        city = filters.get("city")
        if city and str(metadata.get("city", metadata.get("L_City", ""))).lower() != str(city).lower():
            return False
        return True


services = NLPServices()


async def cached_compute(operation: str, payload: BaseModel, compute: Any) -> tuple[Any, bool]:
    key = cache_key(operation, payload)
    cached = cache.get(key)
    if cached is not None:
        return cached, True
    # Existing NLP components are synchronous and can be CPU intensive. Keep
    # them off the event loop so concurrent health and API requests stay live.
    value = await run_in_threadpool(compute)
    cache.set(key, value)
    return value, False


@asynccontextmanager
async def lifespan(_: FastAPI):
    log_event("application_started")
    if settings.db_autoload:
        await run_in_threadpool(services.load_documents_from_database)
    elif settings.listings_path:
        await run_in_threadpool(services.load_documents_from_file, settings.listings_path)
    yield
    log_event("application_stopped")


app = FastAPI(
    title="Real Estate NLP API",
    description="Search, query parsing, entity extraction, summarization, and fair-housing compliance checks.",
    version="1.0.0",
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"])


@app.middleware("http")
async def rate_limit_and_log(request: Request, call_next: Any) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))[:128]
    client_ip = request.client.host if request.client else "unknown"
    allowed, remaining, retry_after = limiter.allow(client_ip)
    started = time.perf_counter()
    if not allowed:
        response = JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS, content={"detail": "Rate limit exceeded. Try again shortly.", "request_id": request_id}, headers={"Retry-After": str(max(1, math.ceil(retry_after)))})
    else:
        response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-RateLimit-Limit"] = str(limiter.limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    log_event("http_request", request_id=request_id, method=request.method, path=request.url.path, status_code=response.status_code, duration_ms=round((time.perf_counter() - started) * 1000, 2), client_ip=client_ip)
    return response


@app.get("/", tags=["system"])
async def root() -> dict[str, Any]:
    return {"name": app.title, "version": app.version, "docs": "/docs"}


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/ready", tags=["system"])
async def ready() -> dict[str, Any]:
    database = services.database_state
    return {
        "status": "ready" if database["status"] != "error" else "degraded",
        "documents": services.document_count,
        "database": database,
    }


@app.post("/search", response_model=SearchResponse, tags=["nlp"])
async def search(request: SearchRequest, response: Response) -> dict[str, Any]:
    def compute() -> dict[str, Any]:
        filters, _ = services.parse(request.query)
        results = services.search(request, filters)
        return {"query": request.query, "results": results, "count": len(results), "parsed_filters": filters}
    try:
        value, hit = await cached_compute(f"search:v{services.documents_version}", request, compute)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return value


@app.post("/parse-query", tags=["nlp"])
async def parse_query(request: ParseQueryRequest, response: Response) -> dict[str, Any]:
    def compute() -> dict[str, Any]:
        filters, sql_result = services.parse(request.query)
        result: dict[str, Any] = {"query": request.query, "filters": filters}
        if request.include_sql:
            result["sql"], result["parameters"] = sql_result if sql_result else (None, [])
        return result
    try:
        value, hit = await cached_compute("parse-query", request, compute)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return value


@app.post("/extract-entities", tags=["nlp"])
async def extract_entities(request: TextRequest, response: Response) -> dict[str, Any]:
    value, hit = await cached_compute("extract-entities", request, lambda: services.entities(request.text))
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return value


@app.post("/summarize", tags=["nlp"])
async def summarize(request: SummarizeRequest, response: Response) -> dict[str, Any]:
    def compute() -> dict[str, Any]:
        sentences = [part.strip() for part in SENTENCE_PATTERN.split(request.text) if part.strip()] or [request.text.strip()]
        entities = services.entities(request.text)
        keywords = {str(value).lower() for value in entities.get("amenities", [])}
        scored = []
        for index, sentence in enumerate(sentences):
            normalized = sentence.replace(",", "").lower()
            score = (2 if index == 0 else 0) + sum(keyword in normalized for keyword in keywords)
            score += sum(entities.get(field) is not None and str(entities[field]) in normalized for field in ("bedrooms", "bathrooms", "price", "sqft"))
            scored.append((score, index, sentence))
        chosen = sorted(sorted(scored, key=lambda item: (-item[0], item[1]))[:request.max_sentences], key=lambda item: item[1])
        summary = " ".join(item[2] for item in chosen)
        if len(summary) > request.max_characters:
            summary = summary[:request.max_characters - 1].rstrip() + "…"
        return {"summary": summary, "sentence_count": len(chosen), "original_characters": len(request.text)}
    value, hit = await cached_compute("summarize", request, compute)
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return value


@app.post("/check-compliance", tags=["nlp"])
async def check_compliance(request: ComplianceRequest, response: Response) -> dict[str, Any]:
    value, hit = await cached_compute("check-compliance", request, lambda: services.compliance(request.text, request.text_type))
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return value


@app.put("/documents", tags=["search"])
async def replace_documents(request: DocumentsRequest) -> dict[str, Any]:
    try:
        count = services.replace_documents(request.documents)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"documents": count, "cache_entries_invalidated": cache.clear()}


@app.post("/documents/reload", tags=["search"])
async def reload_documents() -> dict[str, Any]:
    database = await run_in_threadpool(services.load_documents_from_database)
    if database["status"] == "error":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Could not load listings from the database.",
                "database": database,
            },
        )
    return {"documents": services.document_count, "database": database}


@app.get("/cache/stats", tags=["operations"])
async def cache_stats() -> dict[str, int]:
    return cache.stats()


@app.delete("/cache", tags=["operations"])
async def clear_cache() -> dict[str, int]:
    return {"entries_removed": cache.clear()}
